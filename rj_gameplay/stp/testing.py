from stp.rc import Robot, WorldState, GameInfo, Field


@classmethod
def generate_test_robot(cls,
                        robot_id: RobotId,
                        is_ours: bool = True,
                        pose: np.ndarray = np.array([0.0, 0.0, 0.0]),
                        twist: np.ndarray = np.array([0.0, 0.0, 0.0]),
                        ball_sense_triggered=False):
    """
    Returns a robot with default options for use in testing
    """
    bot = cls(robot_id,
              is_ours,
              pose,
              twist,
              ball_sense_triggered=ball_sense_triggered,
              visible=True,
              has_ball_sense=True,
              kicker_charged=True,
              kicker_healthy=True,
              lethal_fault=False)
        return bot


@classmethod
def generate_test_ball(cls,
                       pos: np.ndarray = np.array([0.0, 0.0]),
                       vel: np.ndarray = np.array([0.0, 0.0]),
                       visible: bool = True):
    ball = cls(pos, vel, visible)
    return ball


@classmethod
def generate_divA_field(cls):
    """
    Generate a division A field

    Penalty distances and "goal_flat" need to be fixed
    """
    field = cls(length_m=12.0,
                width_m=9.0,
                border_m=0.3,
                line_width_m=0.01,
                goal_width_m=1.8,
                goal_depth_m=0.18,
                goal_height_m=0.16,
                penalty_short_dist_m=float('nan'),
                penalty_long_dist_m=float('nan'),
                center_radius_m=0.5,
                center_diameter_m=1.0,
                goal_flat_m=float('nan'),
                floor_length_m=13.4,
                floor_width_m=10.04)
    return field


@classmethod
def generate_divB_field(cls):
    """
    Generate a division B field

    Penalty distances and "goal_flat" need to be fixea

    Note, penalty distances are width and deapth of the penalty area
    """
    field = cls(length_m=9.0,
                width_m=6.0,
                border_m=0.3,
                line_width_m=0.01,
                goal_width_m=1.0,
                goal_depth_m=0.18,
                goal_height_m=0.16,
                penalty_short_dist_m=float('nan'),
                penalty_long_dist_m=float('nan'),
                center_radius_m=0.5,
                center_diameter_m=1.0,
                goal_flat_m=float('nan'),
                floor_length_m=10.04,
                floor_width_m=7.4)
    return field

@classmethod
def generate_our_field(cls):
    """
    Generates the practice field that we have
    """
    raise NotImplementedError(
        "Our field specifications need to be entered")
    #field = cls(length_m = 5918, width_m = , border_m = 0.3, line_width_m = 0.01, goal_width_m = 1.0, goal_depth_m = 0.18, goal_height_m = 0.16, penalty_short_dist_m = float('nan'), penalty_long_dist_m = float('nan'), center_radius_m = 0.5, center_diameter_m = 1.0, goal_flat_m = float('nan'), floor_length_m: 10.04, floor_width_m = 7.4):
    #return field



@classmethod
def generate_test_playing_gameinfo(cls):
    info = cls(GamePeriod.FIRST_HALF, GameState.PLAYING, GameRestart.NONE,
               False)
        return info


@classmethod
def generate_test_worldstate(
    cls,
    our_robots=[],
    their_robots=[],
    ball=Ball.generate_test_ball(),
    game_info=GameInfo.generate_test_playing_gameinfo(),
    field=Field.generate_divB_field()):
    """
    generates a test worldstate
    """
    our_bots = our_robots
    their_bots = their_robots
    world = cls(our_bots, their_bots, ball, game_info, field)
    return world






