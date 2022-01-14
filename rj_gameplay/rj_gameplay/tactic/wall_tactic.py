from dataclasses import dataclass
from typing import List, Optional
from typing import Dict, Generic, List, Optional, Tuple, Type, TypeVar

import stp.action as action
import stp.rc as rc
import stp.tactic as tactic
import stp.role as role

import rj_gameplay.eval
import rj_gameplay.skill as skills
from rj_gameplay.skill import move
import stp.skill as skill
import numpy as np

# TODO: replace w/ global param server
from stp.utils.constants import RobotConstants, BallConstants
import stp.global_parameters as global_parameters

from rj_msgs.msg import RobotIntent

MIN_WALL_RAD = None


class WallTactic(tactic.Tactic):
    def __init__(self, robot: rc.Robot, wall_ct: int):
        super().__init__(robot)

        self.wall_ct = wall_ct
        self.move_skill = None

    def pass_wall_pts(self, wall_pts) -> None:
        self.wall_pts = wall_pts

    def tick(self, world_state: rc.WorldState) -> RobotIntent:
        # create skill with correct target & face_point
        if self.move_skill is None:
            self.move_skill = move.Move(
                robot=self.robot,
                target_point=self.wall_pts[self.wall_ct],
                face_point=world_state.ball.pos,
            )

        # tick skill and return
        intent = self.move_skill.tick(world_state)
        return intent

    def is_done(self, world_state):
        # waller never ends
        return False
