"""Tactic to produce goalie behavior, which tracks the ball, moves to block if a shot on goal is taken, and stays within the goalie box (generally)."""

from dataclasses import dataclass
from typing import List, Optional
from typing import Dict, Generic, List, Optional, Tuple, Type, TypeVar

import stp.action as action
import stp.rc as rc
import stp.tactic as tactic
import stp.role as role

import rj_gameplay.eval
import rj_gameplay.skill as skills
from rj_gameplay.skill import move, receive, pivot_kick  #, intercept
import stp.skill as skill
import numpy as np
# TODO: replace w/ global param server
from stp.utils.constants import RobotConstants, BallConstants
import stp.global_parameters as global_parameters
from stp.local_parameters import Param

# TODO: param server this const
MIN_WALL_RAD = 0
GOALIE_PCT_TO_BALL = 0.15


class GoalieCost(role.CostFn):
    def __call__(
            self,
            robot: rc.Robot,
            prev_result: Optional["RoleResult"],
            world_state: rc.WorldState,
    ) -> float:
        if world_state.game_info is not None:
            if robot.id == world_state.goalie_id:
                return 0.0

        return 10000000


def get_goalie_pt(world_state: rc.WorldState) -> np.ndarray:
    """Finds point for goalie to best be in to block a shot.
    :return numpy point
    """
    # TODO: param server any constant from stp/utils/constants.py (this includes BallConstants)
    ball_pt = world_state.ball.pos
    goal_pt = world_state.field.our_goal_loc

    dir_vec = (ball_pt - goal_pt) / np.linalg.norm(ball_pt - goal_pt)
    # get in-between ball and goal, staying behind wall
    dist_from_goal = min(
        GOALIE_PCT_TO_BALL * np.linalg.norm(ball_pt - goal_pt),
        MIN_WALL_RAD - RobotConstants.RADIUS * 2.1)
    mid_pt = goal_pt + (dir_vec * dist_from_goal)
    return mid_pt


def get_block_pt(world_state: rc.WorldState, my_pos: np.ndarray) -> np.ndarray:
    pos = world_state.ball.pos
    vel = world_state.ball.vel

    block_pt = np.array([(my_pos[1] - pos[1]) / vel[1] * vel[0] + pos[0],
                         my_pos[1]])

    return block_pt


class GoalieTactic(tactic.ITactic):
    def __init__(self):

        # init skills
        self.move_se = tactic.SkillEntry(move.Move())
        self.receive_se = tactic.SkillEntry(receive.Receive())
        self.pivot_kick_se = tactic.SkillEntry(pivot_kick.PivotKick(None, target_point = np.array([0.0, 6.0]), chip=True, kick_speed=6.0))

        # TODO: rename cost_list to role_cost in other gameplay files
        self.role_cost = GoalieCost()

    def compute_props(self):
        pass

    def create_request(self, **kwargs) -> role.RoleRequest:
        """Creates a sane default RoleRequest.
        :return: A list of size 1 of a sane default RoleRequest.
        """
        pass

    def get_requests(self, world_state: rc.WorldState,
                     props) -> List[tactic.RoleRequests]:
        global MIN_WALL_RAD
        """
        :return: A list of role requests for move skills needed
        """

        # TODO: this calculation is copy-pasted from wall_tactic
        # put into common param file: https://www.geeksforgeeks.org/global-keyword-in-python/

        # dist is slightly greater than penalty box bounds
        box_w = world_state.field.penalty_long_dist_m
        box_h = world_state.field.penalty_short_dist_m
        line_w = world_state.field.line_width_m
        MIN_WALL_RAD = RobotConstants.RADIUS + line_w + np.hypot(
            box_w / 2, box_h)

        role_requests = {}
        if world_state and world_state.ball.visible:
            ball_speed = np.linalg.norm(world_state.ball.vel)
            ball_dist = np.linalg.norm(world_state.field.our_goal_loc -
                                       world_state.ball.pos)

            if ball_speed < 1.0 and ball_dist < MIN_WALL_RAD - RobotConstants.RADIUS * 2.1:
                self.move_se = tactic.SkillEntry(move.Move())
                if not self.receive_se.skill.is_done(world_state): 
                    # if ball is slow and inside goalie box, collect it
                    role_requests[self.receive_se] = [
                        role.RoleRequest(role.Priority.HIGH, True, self.role_cost)
                    ]
                else:
                    # if ball has been stopped already, chip toward center field
                    self.pivot_kick_se.skill.target_point = np.array([0.0, 6.0])
                    role_requests[self.pivot_kick_se] = [
                        role.RoleRequest(role.Priority.HIGH, True, self.role_cost)
                    ]
            else:
                ball_to_goal_time = ball_dist / ball_speed
                if ball_speed > 0 and ball_to_goal_time < 2:
                    # if ball is moving and coming at goal, move laterally to block ball
                    # TODO (#1676): replace this logic with a real intercept planner
                    self.move_se.skill.target_point = get_block_pt(
                        world_state, get_goalie_pt(world_state))
                    self.move_se.skill.face_point = world_state.ball.pos
                    role_requests[self.move_se] = [
                        role.RoleRequest(role.Priority.HIGH, True,
                                         self.role_cost)
                    ]
                else:
                    # else, track ball normally
                    self.move_se.skill.target_point = get_goalie_pt(
                        world_state)
                    self.move_se.skill.face_point = world_state.ball.pos
                    role_requests[self.move_se] = [
                        role.RoleRequest(role.Priority.HIGH, True,
                                         self.role_cost)
                    ]
        if self.pivot_kick_se.skill.is_done(world_state):
            self.pivot_kick_se = tactic.SkillEntry(pivot_kick.PivotKick(None, target_point = np.array([0.0, 6.0]), chip=True, kick_speed=6.0))

        return role_requests

    def tick(self,
             role_results: tactic.RoleResults) -> List[tactic.SkillEntry]:
        """
        :return: A list of skills depending on which roles are filled
        """

        # create list of skills based on if RoleResult exists for SkillEntry
        skills = []

        move_result = role_results[self.move_se]
        receive_result = role_results[self.receive_se]
        pivot_kick_result = role_results[self.pivot_kick_se]

        # move skill takes priority
        if move_result and move_result[0].is_filled():
            skills.append(self.move_se)
        elif receive_result and receive_result[0].is_filled():
            skills.append(self.receive_se)
        elif pivot_kick_result and pivot_kick_result[0].is_filled():
            skills.append(self.pivot_kick_se)

        return skills

    def is_done(self, world_state):
        """
        :return boolean indicating if tactic is done
        """
        # goalie tactic always active
        return False
