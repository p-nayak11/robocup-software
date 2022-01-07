import stp.play
import stp.tactic

from rj_gameplay.tactic import move_tactic
import stp.skill
import stp.role
import stp.role.cost
from stp.role.assignment.naive import NaiveRoleAssignment
import stp.rc
from typing import (
    Dict,
    List,
    Tuple,
    Optional,
    Type,
)
import numpy as np
from rj_msgs.msg import RobotIntent

class LineUp(stp.play.Play):
    """Play that lines up all six robots on the side of the field."""

    def __init__(self):
        super().__init__()

        # compute move points
        start = (3.0, 0.0)
        dy = 0.5
        self.move_points = [(start[0], start[1] + i * dy) for i in range(6)]

        # fill cost functions by priority
        # "hardcode" robot ids to line up
        # self.ordered_costs = [stp.role.cost.PickRobotById(5-i) for i in range(6)]

        # OR assign closest robot to each point to go
        self.ordered_costs = [stp.role.cost.PickClosestRobot(pt) for pt in self.move_points]

        # fill roles
        self.ordered_roles = [move_tactic.MoveTactic for _ in range(6)]

        # filled by assign_roles() later
        self.ordered_tactics = []

    def tick(
        self,
        world_state: stp.rc.WorldState,
    ) -> List[RobotIntent]:

        # if no tactics created, assign roles and create them
        if not self.ordered_tactics:
            self.assign_roles(world_state)

        # return robot intents from assigned tactics back to gameplay node
        return self.get_robot_intents(world_state)

    def init_new_tactics(self, assigned_robots: List[stp.rc.Robot], world_state: stp.rc.WorldState) -> None:

        for role, robot, pt in zip(self.ordered_roles, assigned_robots, self.move_points):
            new_tactic = None
            # TODO: this is bad, shouldn't have to check types of tactics imo
            # the only role in this play is the move tactic, but in other plays there will be more
            # although perhaps this is fine since the play has to manually fill ordered_roles dynamically anyhow, indicating it knows what roles to expect
            if role is move_tactic.MoveTactic:
                new_tactic = role(robot, pt, (0.0, 0.0))

            if new_tactic is not None:
                self.ordered_tactics.append(new_tactic)
