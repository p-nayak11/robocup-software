import standard_play
import behavior
import skills
import tactics
import robocup
import constants
import main


class OurCornerKickTouch(standard_play.StandardPlay):

    MinChipRange = 0.3
    MaxChipRange = 3.0
    ChipperPower = 0.5
    TargetSegmentWidth = 1.5
    MaxKickSpeed = 0.5
    MaxKickAccel = 0.5
    Running = False

    def __init__(self, indirect=None):
        super().__init__(continuous=True)


        # setup a line kick skill to replace the pivotkick since a pivot would easily cause a double touch
        self.kicker = skills.line_kick.LineKick()
        self.kicker.chip_power = OurCornerKickTouch.ChipperPower  # TODO: base this on the target dist from the bot
        self.kicker.min_chip_range = OurCornerKickTouch.MinChipRange
        self.kicker.max_chip_range = OurCornerKickTouch.MaxChipRange
        self.kicker.max_speed = OurCornerKickTouch.MaxKickSpeed
        self.kicker.max_accel = OurCornerKickTouch.MaxKickAccel

        # larger avoid ball radius for line kick setup so we don't run over the ball backwards
        self.kicker.setup_ball_avoid = constants.Field.CenterRadius - constants.Robot.Radius
        self.kicker.drive_around_dist = constants.Field.CenterRadius - constants.Robot.Radius

        # create a one touch pass behavior with line kick as the kicker skill
        self.pass_bhvr = tactics.one_touch_pass.OneTouchPass(self.kicker)

        # add transistions for when the play is done
        self.add_transition(behavior.Behavior.State.start,
                            behavior.Behavior.State.running, lambda: True,
                            'immediately')

        self.add_transition(behavior.Behavior.State.running,
                            behavior.Behavior.State.completed,
                            self.pass_bhvr.is_done_running, 'passing is done')

        # start the actual pass
        self.add_subbehavior(self.pass_bhvr, 'pass')

    @classmethod
    def score(cls):
        gs = main.game_state()

        # enter play when doing a corner kick or stay in it even if we manipulate the ball
        if OurCornerKickTouch.Running or (gs.is_ready_state() and (gs.is_our_direct() or gs.is_our_indirect() or gs.is_our_free_kick()) and main.ball().pos.y > (
                constants.Field.Length - 2) and abs(main.ball().pos.x) > .5 ):
            OurCornerKickTouch.Running = True
            return 0
        else:
            return float("inf")

    @classmethod
    def is_restart(cls):
        return True


    def execute_running(self):
        # exit the play when the pass is done
        if self.pass_bhvr.is_done_running():
            OurCornerKickTouch.Running = True
