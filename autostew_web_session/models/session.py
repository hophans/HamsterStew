import logging

from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import QuerySet, Max, Min

import autostew_web_session.models.participant
from autostew_web_enums.models import SessionState
from autostew_web_session.models.member import Member


class SessionSetup(models.Model):
    class Meta:
        ordering = ['name']

    name = models.CharField(max_length=100, blank=True)
    is_template = models.BooleanField(db_index=True)

    server_controls_setup = models.BooleanField(
            help_text="If true, players won't be able to control the race setup")
    server_controls_track = models.BooleanField(
            help_text="If true, players won't be able to control track selection")
    server_controls_vehicle_class = models.BooleanField(
            help_text="If true, players won't be acle to control vehicle class selection")
    server_controls_vehicle = models.BooleanField(
            help_text="If true, players won't be able to access vehicle selection")
    grid_size = models.IntegerField(
            help_text="How many cars can be on the field, don't set it higher than the track's grid size")
    max_players = models.IntegerField(
            help_text="How many human players can join the game")
    opponent_difficulty = models.IntegerField(default=100,
                                              help_text="AI difficulty, 0 to 100")

    force_identical_vehicles = models.BooleanField()
    allow_custom_vehicle_setup = models.BooleanField()
    force_realistic_driving_aids = models.BooleanField()
    abs_allowed = models.BooleanField(
            help_text="Won't have any effect if force realistic driving aids is on")
    sc_allowed = models.BooleanField(
            help_text="Won't have any effect if force realistic driving aids is on")
    tcs_allowed = models.BooleanField(
            help_text="Won't have any effect if force realistic driving aids is on")
    force_manual = models.BooleanField(
            help_text="If true, only manual transmission will be allowed")
    rolling_starts = models.BooleanField(
            help_text="If true, the race will have a rolling start")
    force_same_vehicle_class = models.BooleanField()
    fill_session_with_ai = models.BooleanField()
    mechanical_failures = models.BooleanField()
    auto_start_engine = models.BooleanField()
    timed_race = models.BooleanField(
            "If true, race length will be measured in minutes")
    ghost_griefers = models.BooleanField()
    enforced_pitstop = models.BooleanField()

    practice1_length = models.IntegerField(help_text="In minutes", default=0)
    practice2_length = models.IntegerField(help_text="In minutes", default=0)
    qualify_length = models.IntegerField(help_text="In minutes", default=0)
    warmup_length = models.IntegerField(help_text="In minutes", default=0)
    race1_length = models.IntegerField(help_text="In laps or minutes", default=5)
    race2_length = models.IntegerField(help_text="In laps or minutes (this setting does not have any effect (yet?)",
                                       default=0)

    privacy = models.ForeignKey('autostew_web_enums.PrivacyDefinition', null=True)
    damage = models.ForeignKey('autostew_web_enums.DamageDefinition', null=True)
    tire_wear = models.ForeignKey('autostew_web_enums.TireWearDefinition', null=True)
    fuel_usage = models.ForeignKey('autostew_web_enums.FuelUsageDefinition', null=True)
    penalties = models.ForeignKey('autostew_web_enums.PenaltyDefinition', null=True)
    allowed_views = models.ForeignKey('autostew_web_enums.AllowedViewsDefinition', null=True)
    track = models.ForeignKey('Track', null=True, blank=True)
    vehicle_class = models.ForeignKey('VehicleClass', null=True, blank=True,
                                      help_text="Only has a real effect if force_same_vehicle_class")
    vehicle = models.ForeignKey('Vehicle', null=True, blank=True,
                                help_text="Only has a real effect if force_same_vehicle")
    date_year = models.IntegerField(help_text="Race date, set to 0 for 'real date'", default=0)
    date_month = models.IntegerField(help_text="Race date, set to 0 for 'real date'", default=0)
    date_day = models.IntegerField(help_text="Race date, set to 0 for 'real date'", default=0)
    date_hour = models.IntegerField(default=9)
    date_minute = models.IntegerField(default=0)
    date_progression = models.IntegerField(default=1,
                                           help_text="Time multiplier, unconfirmed allowed values: "
                                                     "0, 1, 2, 5, 10, 30, 60")
    weather_progression = models.IntegerField(default=1,
                                              help_text="Weather progression multiplier, "
                                                        "unconfirmed allowed values: 0, 1, 2, 5, 10, 30, 60")
    weather_slots = models.IntegerField(default=0,
                                        help_text="Set to 0 for 'real weather'"
                                        )
    weather_1 = models.ForeignKey('autostew_web_enums.WeatherDefinition', related_name='+', null=True, blank=True)
    weather_2 = models.ForeignKey('autostew_web_enums.WeatherDefinition', related_name='+', null=True, blank=True)
    weather_3 = models.ForeignKey('autostew_web_enums.WeatherDefinition', related_name='+', null=True, blank=True)
    weather_4 = models.ForeignKey('autostew_web_enums.WeatherDefinition', related_name='+', null=True, blank=True)
    game_mode = models.ForeignKey('autostew_web_enums.GameModeDefinition', related_name='+', null=True, blank=True)

    def get_race_length_unit(self):
        return "minutes" if self.timed_race else "laps"

    def get_vehicle_restriction(self):
        if self.force_identical_vehicles:
            return self.vehicle_class
        if self.force_same_vehicle_class:
            return self.vehicle.vehicle_class
        return None

    def get_track_url(self):
        if self.force_identical_vehicles:
            get = '?vehicle={}'.format(self.vehicle.ingame_id)
        elif self.force_same_vehicle_class:
            get = '?vehicle_class={}'.format(self.vehicle_class.ingame_id)
        else:
            get = ''
        return "{}{}".format(self.track.get_absolute_url(), get)

    def get_absolute_url(self):
        return reverse('session:setup', args=[str(self.id)])

    def get_fields(self):
        return [(field.verbose_name, field._get_val_from_obj(self)) for field in self.__class__._meta.fields]

    def __str__(self):
        return "{} ({})".format(self.name, "template" if self.is_template else "instance")


class Session(models.Model):
    class Meta:
        ordering = ['start_timestamp']

    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')
    server = models.ForeignKey('Server')
    setup_template = models.ForeignKey(SessionSetup, limit_choices_to={'is_template': True}, related_name='+',
                                       help_text="This setup is feeded to the game")
    setup_actual = models.ForeignKey(SessionSetup, limit_choices_to={'is_template': False}, related_name='+',
                                     null=True, blank=True,
                                     help_text="This setup is read from the game once the race starts")

    start_timestamp = models.DateTimeField(auto_now_add=True,  # TODO remove auto_now_add
                                           help_text="Time when the race starts/started")
    last_update_timestamp = models.DateTimeField(auto_now=True)
    schedule_time = models.TimeField(null=True, blank=True, help_text="Time this schedule will run")
    schedule_date = models.DateField(null=True, blank=True,
                                     help_text="Date this schedule will run, if blank will run daily")
    running = models.BooleanField(help_text="If true, this race is currently running", db_index=True)
    finished = models.BooleanField(help_text="If true, this race finished", db_index=True)

    max_member_count = models.IntegerField(null=True, blank=True)

    first_snapshot = models.ForeignKey("self", null=True, blank=True, related_name='+')

    fastest_lap = models.ForeignKey('Lap', null=True, blank=True, related_name='+')

    is_result = models.BooleanField(default=False, db_index=True)
    is_final_result = models.BooleanField(default=False, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    session_state = models.ForeignKey("autostew_web_enums.SessionState", null=True, blank=True)
    session_stage = models.ForeignKey("autostew_web_enums.SessionStage", null=True, blank=True)
    session_phase = models.ForeignKey("autostew_web_enums.SessionPhase", null=True, blank=True)
    session_time_elapsed = models.BigIntegerField(default=0, null=True)
    session_time_duration = models.IntegerField(default=0, null=True)
    num_participants_valid = models.IntegerField(default=0, null=True)
    num_participants_disq = models.IntegerField(default=0, null=True)
    num_participants_retired = models.IntegerField(default=0, null=True)
    num_participants_dnf = models.IntegerField(default=0, null=True)
    num_participants_finished = models.IntegerField(default=0, null=True)
    current_year = models.IntegerField(default=0, null=True)
    current_month = models.IntegerField(default=0, null=True)
    current_day = models.IntegerField(default=0, null=True)
    current_hour = models.IntegerField(default=0, null=True)
    current_minute = models.IntegerField(default=0, null=True)
    rain_density_visual = models.IntegerField(default=0, null=True)
    wetness_path = models.IntegerField(default=0, null=True)
    wetness_off_path = models.IntegerField(default=0, null=True)
    wetness_avg = models.IntegerField(default=0, null=True)
    wetness_predicted_max = models.IntegerField(default=0, null=True)
    wetness_max_level = models.IntegerField(default=0, null=True)
    temperature_ambient = models.IntegerField(default=0, null=True)
    temperature_track = models.IntegerField(default=0, null=True)
    air_pressure = models.IntegerField(default=0, null=True)

    def create_snapshot(self):
        logging.info("Creating session snapshot")
        snapshot = Session.objects.get(pk=self.pk)
        snapshot.pk = None
        snapshot.parent = self
        snapshot.save()

        for member in self.member_set.all():
            member.create_snapshot(snapshot)

        for participant in self.participant_set.all():
            participant.create_snapshot(snapshot)

        self.save()
        return snapshot

    def get_absolute_url(self):
        return reverse('session:session', args=[str(self.id)])

    def __str__(self):
        return "{track} {restriction} {length} {unit}".format(
                track=self.setup_actual.track.name,
                restriction=self.setup_actual.get_vehicle_restriction() if self.setup_actual.get_vehicle_restriction() else "any car",
                length=self.setup_actual.race1_length,
                unit=self.setup_actual.get_race_length_unit(),
        )

    def get_connected_members(self) -> QuerySet:
        return self.member_set.filter(still_connected=True)

    def get_members_who_finished_race(self) -> QuerySet:
        if self.parent_or_self.is_result:
            return self.parent_or_self.member_set.filter(still_connected=True)
        return None

    def get_members_who_participated(self):
        participants = autostew_web_session.models.participant.Participant.objects.filter(lap__in=self.lap_set.all())
        return Member.objects.filter(participant__in=participants)

    def reorder_by_best_time(self):
        participants_with_fastest_lap_set = self.participant_set.filter(fastest_lap_time__gt=0, still_connected=True)
        for i, v in enumerate(participants_with_fastest_lap_set.order_by('fastest_lap_time')):
            v.race_position = i + 1
            v.save()
        positions_without_laptime = len(participants_with_fastest_lap_set) + 1
        for v in self.participant_set.filter(fastest_lap_time=0) | self.participant_set.filter(still_connected=False):
            v.race_position = positions_without_laptime
            v.save()

    def get_connected_participants(self):
        return self.participant_set.filter(still_connected=True) | self.participant_set.filter(has_final_result=True)

    def get_disconnected_participants(self):
        return self.participant_set.filter(still_connected=False, has_final_result=False)

    def get_nice_state(self):
        if self.session_state.name == SessionState.race:
            return self.session_stage.name
        return self.session_state.name

    @property
    def parent_or_self(self):
        return self.parent if self.parent is not None else self

    @property
    def previous_in_session(self):
        try:
            target_id = Session.objects.filter(
                    id__lt=self.id,
                    parent=self.parent_or_self,
            ).aggregate(Max('id'))['id__max']
            return Session.objects.get(pk=target_id)
        except self.DoesNotExist:
            return None

    @property
    def next_in_session(self):
        try:
            target_id = Session.objects.filter(
                    id__gt=self.id,
                    parent=self.parent_or_self,
            ).aggregate(Min('id'))['id__min']
            return Session.objects.get(pk=target_id)
        except self.DoesNotExist:
            return None
