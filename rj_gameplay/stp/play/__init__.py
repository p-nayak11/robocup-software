""" This module contains data structures for the Plays level of STP.
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import (
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
)

import stp.action
import stp.skill
import stp.rc
import stp.role
import stp.role.assignment
import stp.tactic
import stp.utils.enum
import stp.utils.typed_key_dict

from rj_msgs.msg import RobotIntent

PropT = TypeVar("PropT")

# TODO: move to stp.role
# roles = un-initialized Tactics
Role = Type[stp.tactic.Tactic]

class IPlay(ABC):
    pass

class Play(ABC):
    """Coordinate full-team behaviors via Tactics. Assumes number of roles matches number of robots on the field. See tick() for more details."""

    def __init__(self):
        # TODO: all three of these are required for assign_roles()
        # should I make these abstract to force subclasses to use? 
        # https://stackoverflow.com/questions/23831510/abstract-attribute-not-property
        #
        # or should it just be part of a RoleAssign class with passed in params?
        # that kicks the problem down to forcing roles to have a RoleAssign property, I suppose
        self.ordered_costs: List[stp.role.costFn] = []
        self.ordered_roles: List[Role] = []
        self.ordered_tactics: List[stp.tactic.ITactic] = []

    @abstractmethod
    def tick(
        self,
        world_state: stp.rc.WorldState,
    ) -> List[RobotIntent]:
        """Performs one "tick" of the specified play.

        This should:
            1. Determine if role assignment is necessary.
            2. If so, perform role assignment with self.assign_roles().
            3. Tick tactics to aggregate robot_intents with self.get_robot_intents().

        :param world_state: Current state of the world.
        :return: list of robot intents where index = robot_id
        """
        ...

    # TODO: add typing when finalized
    def assign_roles(
        self,
        world_state: stp.rc.WorldState,
    ) -> None:
        """Given that all roles are in sorted order of priority, greedily assign the highest-priority role to the lowest-cost robot for that role. Instantiate tactics with the correct robots post-assignment."""

        assigned_robots = []
        # TODO: make rc.Robot hashable by id to avoid this
        used_robot_ids = set()
        for cost_fn in self.ordered_costs:
            min_cost = 1e9
            cheapest_robot = None
            for robot in world_state.our_robots:
                if robot.id in used_robot_ids: continue
                cost = cost_fn(robot, world_state)
                print(robot.id, cost)
                if cost < min_cost:
                    min_cost = cost
                    cheapest_robot = robot

            if cheapest_robot is None:
                # TODO: properly error handle if cheapest_robot is None
                print(f"cost_fn {cost_fn} was not assigned")

            used_robot_ids.add(cheapest_robot.id)
            assigned_robots.append(cheapest_robot)
            print(used_robot_ids)

        for rob in assigned_robots:
            print(rob.id)
        self.init_tactics(assigned_robots)

    @abstractmethod
    def init_tactics(self, assigned_robots: List[stp.rc.Robot]) -> None:
        """After self.ordered_costs is filled, instantiate each Tactic with its new robot and the parameters each Tactic needs.
        """
        ...

    def get_robot_intents(self, world_state: stp.rc.WorldState) -> List[RobotIntent]:
        """Given assigned roles in self.ordered_tactics, tick each tactic and aggregate the results in one List, where indices are robot_ids and values are RobotIntents. GameplayNode then sends these back to motion planning via ROS."""
        robot_intents = [None for _ in self.ordered_tactics]
        for tactic in self.ordered_tactics:
            robot_intent = tactic.tick(world_state)
            robot_id = tactic.robot.id # TODO: enforce existence with getter?
            robot_intents[robot_id] = robot_intent
        return robot_intents
