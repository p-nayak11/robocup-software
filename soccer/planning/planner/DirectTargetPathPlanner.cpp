#include "planning/planner/DirectTargetPathPlanner.hpp"
#include "planning/planner/MotionCommand.hpp"
#include "planning/trajectory/PathSmoothing.hpp"
#include "planning/trajectory/Trajectory.hpp"
#include "planning/trajectory/VelocityProfiling.hpp"
#include <Geometry2d/Pose.hpp>

using namespace Geometry2d;
namespace Planning {

double vectorInDirection(Point point, Point direction) {
    const auto vector = point.dot(direction.normalized());
    return std::max(vector, 0.0);
}

Trajectory DirectTargetPathPlanner::plan(PlanRequest&& planRequest) {
    RobotInstant startInstant {planRequest.start.pose, planRequest.start.velocity, planRequest.start.timestamp};
    const auto& motionConstraints = planRequest.constraints.mot;
    const Geometry2d::ShapeSet& obstacles = planRequest.obstacles;

    const Planning::DirectPathTargetCommand& command = std::get<DirectPathTargetCommand>(planRequest.motionCommand);

    if (shouldReplan(planRequest) || findInvalidTime(planRequest)) {
        Geometry2d::Point endTarget = command.pathGoal.pose.position();
        const Point direction = (endTarget - startInstant.pose.position()).normalized();

        float endSpeed = command.pathGoal.velocity.linear().mag();
        //todo(Ethan) this used to use TrapezoidalPath. that might have been better than this
        std::vector<Point> points = {startInstant.pose.position(), endTarget};
        double viMag = vectorInDirection(startInstant.velocity.linear(), direction);
        double vfMag = vectorInDirection(command.pathGoal.velocity.linear(), direction);
        //this should be a straight line path since vi and vf are collinear
        BezierPath bezier(points, direction.normalized(viMag), direction.normalized(vfMag), motionConstraints);
        Trajectory result = ProfileVelocity(bezier, viMag, vfMag, motionConstraints);
//        path->setStartTime(RJ::now());
        return std::move(result);
    } else {
        return std::move(planRequest.prevTrajectory);
    }
}

//todo(Ethan) fix this this should be implemented in a base class
std::optional<RJ::Seconds> DirectTargetPathPlanner::findInvalidTime(const PlanRequest& request) const {
    if(request.prevTrajectory.empty()) {
        return std::nullopt;
    }
    const auto timeIntoPrevPath = RJ::now() - request.prevTrajectory.begin_time();
    RJ::Seconds invalidTime;
    if (request.prevTrajectory.hit(request.obstacles, timeIntoPrevPath, &invalidTime)) {
        return invalidTime;
    }
    PathTargetCommand command = std::get<PathTargetCommand>(request.motionCommand);

    //todo(Ethan) check dynamic obstacles
    const RobotInstant& last = request.prevTrajectory.last();
    const RobotInstant& goal = command.pathGoal;
    double goalPosDiff = (last.pose.position() - goal.pose.position()).mag();
    double goalVelDiff = (last.velocity.linear() - goal.velocity.linear()).mag();
    if (goalPosDiff > Planner::goalPosChangeThreshold() || goalVelDiff > Planner::goalVelChangeThreshold()) {
        return request.prevTrajectory.duration();
    }
    return std::nullopt;
}

}  // namespace Planning
