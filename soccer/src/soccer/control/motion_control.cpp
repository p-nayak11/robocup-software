#include "motion_control.hpp"

#include <optional>

#include <context.hpp>
#include <rj_common/utils.hpp>
#include <rj_geometry/util.hpp>
#include <rj_utils/logging.hpp>
#include <robot_config.hpp>

#include "planning/instant.hpp"

namespace control {

using rj_geometry::Pose;
using rj_geometry::Twist;
using Planning::RobotInstant;

DEFINE_FLOAT64(params::kMotionControlParamModule, max_acceleration, 1.5, "Maximum acceleration limit (motion control) (m/s^2)");
DEFINE_FLOAT64(params::kMotionControlParamModule, max_velocity, 2.0, "Maximum velocity limit (motion control) (m/s)");
DEFINE_FLOAT64(params::kMotionControlParamModule, rotation_kp, 4.0, "Kp for rotation ((rad/s)/rad)");
DEFINE_FLOAT64(params::kMotionControlParamModule, rotation_ki, 0.0, "Ki for rotation ((rad/s)/(rad*s))");
DEFINE_FLOAT64(params::kMotionControlParamModule, rotation_kd, 0.0, "Kd for rotation ((rad/s)/(rad/s))");
DEFINE_INT64(params::kMotionControlParamModule, rotation_windup, 0, "Windup limit for rotation (unknown units)");
DEFINE_FLOAT64(params::kMotionControlParamModule, translation_kp, 2.0, "Kp for translation ((m/s)/m)");
DEFINE_FLOAT64(params::kMotionControlParamModule, translation_ki, 0.0, "Ki for translation ((m/s)/(m*s))");
DEFINE_FLOAT64(params::kMotionControlParamModule, translation_kd, 0.0, "Kd for translation ((m/s)/(m/s))");
DEFINE_INT64(params::kMotionControlParamModule, translation_windup, 0, "Windup limit for translation (unknown units)");

MotionControl::MotionControl(int shell_id, rclcpp::Node::SharedPtr node, DebugDrawer* debug_drawer)
    : shell_id_(shell_id),
      node_(std::move(node)),
      angle_controller_(0, 0, 0, 50, 0),
      drawer_(debug_drawer) {
    motion_setpoint_pub_ = node_->create_publisher<MotionSetpoint::Msg>(topics::motion_setpoint_pub(shell_id_), rclcpp::QoS(1));
    // Update motion control triggered on world state publish.
    trajectory_sub_ = node_->create_subscription<Planning::Trajectory::Msg>(
        planning::topics::trajectory_pub(shell_id),
        rclcpp::QoS(1),
        [this] (Planning::Trajectory::Msg::SharedPtr trajectory) {
            trajectory_ = rj_convert::convert_from_ros(*trajectory);
            spdlog::info("Got trajectory");
        });
    world_state_sub_ = node_->create_subscription<WorldState::Msg>(
        vision_filter::topics::kWorldStatePub,
        rclcpp::QoS(1),
        [this] (WorldState::Msg::SharedPtr world_state_msg) {
            RobotState state = rj_convert::convert_from_ros(world_state_msg->our_robots.at(shell_id_));

            // TODO(Kyle): Handle the joystick-controlled case here. In the long run we want to convert this to an action. Should we do that now?
            MotionSetpoint setpoint;
            run(state, trajectory_, game_state_, false, &setpoint);
            if (state.visible) {
                motion_setpoint_pub_->publish(rj_convert::convert_to_ros(setpoint));
            }
        });
    game_state_sub_ = node_->create_subscription<GameState::Msg>(
        referee::topics::kGameStatePub,
        rclcpp::QoS(1),
        [this] (GameState::Msg::SharedPtr game_state_msg) {
            game_state_ = rj_convert::convert_from_ros(*game_state_msg).state;
        });
}

void MotionControl::run(const RobotState& state,
                        const Planning::Trajectory& trajectory,
                        const GameState::State& game_state,
                        bool is_joystick_controlled,
                        MotionSetpoint* setpoint) {
    // If we don't have a setpoint (output velocities) or we're under joystick
    // control, reset our PID controllers and exit (but don't force a stop).
    if ((setpoint == nullptr) || is_joystick_controlled) {
        reset();
        return;
    }

    if (!state.visible || trajectory.empty() || game_state == GameState::State::Halt) {
        stop(setpoint);
        return;
    }

    update_params();

    // We run this at 60Hz, so we want to do motion control off of the goal
    // position for the next frame. Evaluate the trajectory there.
    RJ::Seconds dt(1.0 / 60);
    RJ::Time eval_time = state.timestamp + dt;

    std::optional<RobotInstant> maybe_target = trajectory.evaluate(eval_time);
    bool at_end = eval_time > trajectory.end_time();

    // If we're past the end of the trajectory, do motion control off of the
    // end.
    if (at_end) {
        maybe_target = trajectory.last();
    }

    std::optional<Pose> maybe_pose_target;
    Twist velocity_target = Twist::zero();

    // Set up goals from our target motion instant.
    if (maybe_target) {
        auto target = maybe_target.value();
        maybe_pose_target = target.pose;
        velocity_target = target.velocity;
    }

    // TODO: Calculate acceleration and use it to improve response.
    // TODO: Clamp acceleration

    Twist correction = Twist::zero();
    if (maybe_pose_target) {
        Pose error = maybe_pose_target.value() - state.pose;
        error.heading() = fix_angle_radians(error.heading());
        correction = Twist(position_x_controller_.run(static_cast<float>(error.position().x())),
                           position_y_controller_.run(static_cast<float>(error.position().y())),
                           angle_controller_.run(static_cast<float>(error.heading())));
    } else {
        reset();
    }

    // Apply the correction and rotate into the world frame.
    Twist result_world = velocity_target + correction;
    Twist result_body(result_world.linear().rotated(M_PI_2 - state.pose.heading()),
                      result_world.angular());

    // Use default constraints. Planning should be in charge of enforcing
    // constraints on the trajectory, here we just follow it.
    // TODO(#1500): Use this robot's constraints here.
    RobotConstraints constraints;

    if (result_body.linear().mag() > constraints.mot.max_speed) {
        result_body.linear() *= constraints.mot.max_speed / result_body.linear().mag();
    }

    result_body.angular() =
        std::clamp(result_body.angular(), -constraints.rot.max_speed, constraints.rot.max_speed);

    set_velocity(setpoint, result_body);

    // Debug drawing
    if (drawer_ != nullptr)
    {
        if (at_end) {
            drawer_->draw_circle(maybe_target->pose.position(), .15, Qt::red, "Planning");
        } else if (maybe_target) {
            drawer_->draw_circle(maybe_target->pose.position(), .15, Qt::green, "Planning");
        }

        // Line for velocity when we have a target
        if (maybe_pose_target) {
            Pose pose_target = maybe_pose_target.value();
            drawer_->draw_line(pose_target.position(),
                               pose_target.position() + result_world.linear(), Qt::blue,
                               "MotionControl");
        }
    }
}

void MotionControl::set_velocity(MotionSetpoint* setpoint, Twist target_vel) {
    // Limit Velocity
    target_vel.linear().clamp(PARAM_max_velocity);

    // make sure we don't send any bad values
    if (Eigen::Vector3d(target_vel).hasNaN()) {
        target_vel = Twist::zero();
        rj_utils::debug_throw("A bad value was calculated.");
    }

    // Note: we used to set minimum effective speeds here. However, that should
    // really be handled in motion control, because it's just a hack to
    // compensate for static friction effects.
    // It messes up precise shots, so it's been removed.

    // set control values
    setpoint->xvelocity = target_vel.linear().x();
    setpoint->yvelocity = target_vel.linear().y();
    setpoint->avelocity = target_vel.angular();
}

void MotionControl::update_params() {
    // Update PID parameters
    position_x_controller_.kp = static_cast<float>(PARAM_translation_kp);
    position_x_controller_.ki = static_cast<float>(PARAM_translation_ki);
    position_x_controller_.kd = static_cast<float>(PARAM_translation_kd);
    position_x_controller_.setWindup(PARAM_translation_windup);

    position_y_controller_.kp = static_cast<float>(PARAM_translation_kp);
    position_y_controller_.ki = static_cast<float>(PARAM_translation_ki);
    position_y_controller_.kd = static_cast<float>(PARAM_translation_kd);
    position_y_controller_.setWindup(PARAM_translation_windup);

    angle_controller_.kp = static_cast<float>(PARAM_rotation_kp);
    angle_controller_.ki = static_cast<float>(PARAM_rotation_ki);
    angle_controller_.kd = static_cast<float>(PARAM_rotation_kd);
    angle_controller_.setWindup(PARAM_rotation_windup);
}

void MotionControl::reset() {
    position_x_controller_.reset();
    position_y_controller_.reset();
    angle_controller_.reset();
}

void MotionControl::stop(MotionSetpoint* setpoint) {
    *setpoint = {};
    reset();
}

} // namespace control