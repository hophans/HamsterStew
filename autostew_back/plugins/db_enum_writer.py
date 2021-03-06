import json
import logging

from enum import Enum
from django.core.wsgi import get_wsgi_application
from django.db import transaction

from autostew_back.ds_api.event import EventType, LeavingReason
from autostew_back.ds_api.participant import ParticipantState
from autostew_web_enums import models
from autostew_web_session.models.models import Track, VehicleClass, Vehicle, Livery
from autostew_web_enums.models import EventDefinition, GameModeDefinition, TireWearDefinition, PenaltyDefinition, \
    FuelUsageDefinition, AllowedViewsDefinition, PlayerFlagDefinition, WeatherDefinition, DamageDefinition, \
    SessionFlagDefinition, SessionAttributeDefinition, MemberAttributeDefinition, ParticipantAttributeDefinition


name = 'DB enum writer'

get_wsgi_application()

enum_tables = [Track, EventDefinition, SessionFlagDefinition, DamageDefinition, WeatherDefinition,
               PlayerFlagDefinition, AllowedViewsDefinition, FuelUsageDefinition,
               GameModeDefinition, VehicleClass, PenaltyDefinition, Vehicle, Livery, TireWearDefinition,
               ParticipantAttributeDefinition, MemberAttributeDefinition, SessionAttributeDefinition]

true_enums = [
    (EventType, models.EventType),
    (LeavingReason, models.LeavingReason),
    # TODO (MemberLoadState, models.MemberLoadState),
    # TODO (MemberState, models.MemberState),
    (ParticipantState, models.ParticipantState),
    # TODO (SessionState, models.SessionState),
    # TODO (SessionStage, models.SessionStage),
    # TODO (SessionPhase, models.SessionPhase),
]


class ApiListNames(Enum):
    events = 'events'
    tracks = 'tracks'
    vehicles = 'liveries'  # this is intended, as the vehicles list contains only a subset of the liveries list
    game_modes = 'enums/game_mode'
    tire_wears = 'enums/tire_wear'
    penalties = 'enums/penalties'
    participant_attributes = 'attributes/participant'
    fuel_usages = 'enums/fuel_usage'
    vehicle_classes = 'vehicle_classes'
    session_attributes = 'attributes/session'
    allowed_views = 'enums/allowed_view'
    player_flags = 'flags/player'
    weathers = 'enums/weather'
    damage = 'enums/damage'
    member_attributes = 'attributes/member'
    session_flags = 'flags/session'


class ApiListItem:
    def __init__(self, raw):
        self.raw = raw


class ApiTrackList(ApiListItem):
    def __init__(self, raw):
        ApiListItem.__init__(self, raw)
        self.gridsize = raw['gridsize']
        self.name = raw['name']
        self.id = raw['id']


class ApiEventList(ApiListItem):
    def __init__(self, raw):
        ApiListItem.__init__(self, raw)
        self.name = raw['name']
        self.type = raw['type']
        self.description = raw['description']
        self.attributes = raw['attributes']


class ApiVehicleList(ApiListItem):
    def __init__(self, raw, vehicle_classes):
        ApiListItem.__init__(self, raw)
        self.name = raw['name']
        self.id = raw['id']
        self.vehicle_class = vehicle_classes.get_list_items('name', raw['class'])[0]
        self.liveries = ServerList(raw['liveries'], Livery, no_subitems=True, vehicle=self)


class ApiLiveryList(ApiListItem):
    def __init__(self, raw, vehicle):
        ApiListItem.__init__(self, raw)
        self.name = raw['name']
        self.id = raw['id']
        self.vehicle = vehicle


class NameValueItem(ApiListItem):
    def __init__(self, raw):
        ApiListItem.__init__(self, raw)
        self.name = raw['name']
        self.value = raw['value']


class AttributeItem(ApiListItem):
    def __init__(self, raw):
        ApiListItem.__init__(self, raw)
        self.name = raw['name']
        self.type = raw['type']
        self.access = raw['access']
        self.description = raw['description']


# only lists that don't refer to values in others lists can be set here
# lists with references are parsed separately
auto_list_to_types = {
    ApiListNames.events: ApiEventList,
    ApiListNames.tracks: ApiTrackList,
    # ApiListNames.vehicles: Vehicle,  --> cannot be autogenerated, refers to vehicle_class
    ApiListNames.game_modes: NameValueItem,
    ApiListNames.tire_wears: NameValueItem,
    ApiListNames.penalties: NameValueItem,
    ApiListNames.participant_attributes: AttributeItem,
    ApiListNames.member_attributes: AttributeItem,
    ApiListNames.session_attributes: AttributeItem,
    ApiListNames.fuel_usages: NameValueItem,
    ApiListNames.vehicle_classes: NameValueItem,
    ApiListNames.allowed_views: NameValueItem,
    ApiListNames.player_flags: NameValueItem,
    ApiListNames.weathers: NameValueItem,
    ApiListNames.damage: NameValueItem,
    ApiListNames.session_flags: NameValueItem,
}


class ServerList:
    def __init__(self, raw, elem_type, no_subitems=False, **kwargs):
        self.raw = raw
        if no_subitems:
            self.description = None
            self.list = [elem_type(elem, **kwargs) for elem in self.raw]
        else:
            self.description = raw.get('description', None)
            self.list = [elem_type(elem, **kwargs) for elem in self.raw['list']]

    def get_list_items(self, key_field, key_value):
        result = []
        for elem in self.list:
            if elem.raw[key_field] == key_value:
                result.append(elem)
        return result


class ListGenerator:
    def __init__(self, api):
        self._api = api

    def generate_all(self):
        list_raw = self._api.get_lists()
        lists = {}
        for k, v in auto_list_to_types.items():
            list_content = list_raw[k.value]
            lists[k] = ServerList(list_content, v)
        # Vehicles get treated manually to get a Vehicle-to-VehicleClass link
        lists[ApiListNames.vehicles] = ServerList(
            list_raw[ApiListNames.vehicles.value],
            ApiVehicleList,
            vehicle_classes=lists[ApiListNames.vehicle_classes]
        )
        return lists

def env_init(server):
    _recreate_enums(server)


@transaction.atomic
def _recreate_enums(server):
    #_clear_enums()
    _create_enums(server)


def _clear_enums():
    for e in enum_tables:
        e.objects.all().delete()
    for enum, model in true_enums:
        model.objects.all().delete()


def _create_enums(server):
    def _create_name_value(model, listname):
        logging.info("Creating enum {}".format(listname))
        for i in lists[listname].list:
            model(name=i.name, ingame_id=i.value).save(True)

    def _create_attribute(model, listname):
        logging.info("Creating attribute {}".format(listname))
        for i in lists[listname].list:
            model(name=i.name, type=i.type, access=i.access, description=i.description).save(True)

    def _create_true_enum(enum, orm):
        for i in enum:
            orm(name=i.value).save(True)

    for enum, orm in true_enums:
        _create_true_enum(enum, orm)

    lists = ListGenerator(server.api).generate_all()

    _create_name_value(VehicleClass, ApiListNames.vehicle_classes)
    _create_name_value(GameModeDefinition, ApiListNames.game_modes)
    _create_name_value(TireWearDefinition, ApiListNames.tire_wears)
    _create_name_value(PenaltyDefinition, ApiListNames.penalties)
    _create_name_value(FuelUsageDefinition, ApiListNames.fuel_usages)
    _create_name_value(AllowedViewsDefinition, ApiListNames.allowed_views)
    _create_name_value(WeatherDefinition, ApiListNames.weathers)
    _create_name_value(DamageDefinition, ApiListNames.damage)
    _create_name_value(SessionFlagDefinition, ApiListNames.session_flags)

    _create_attribute(SessionAttributeDefinition, ApiListNames.session_attributes)
    _create_attribute(MemberAttributeDefinition, ApiListNames.member_attributes)
    _create_attribute(ParticipantAttributeDefinition, ApiListNames.participant_attributes)

    logging.info("Creating PlayerFlags")
    for pflag in lists[ApiListNames.player_flags].list:
        if pflag.value == 0:
            continue
        PlayerFlagDefinition(name=pflag.name, ingame_id=pflag.value).save(True)

    logging.info("Creating Tracks")
    for track in lists[ApiListNames.tracks].list:
        Track(ingame_id=track.id, name=track.name, grid_size=track.gridsize).save(True)
    logging.info("{} tracks".format(len(lists[ApiListNames.tracks].list)))

    logging.info("Creating Events")
    for event in lists[ApiListNames.events].list:
        EventDefinition(name=event.name, type=event.type, description=event.type, attributes=json.dumps(event.attributes)).save(True)

    logging.info("Creating Vehicles")
    for i, vehicle in enumerate(lists[ApiListNames.vehicles].list):
        if i % 10 == 0 and i > 0:
            logging.info("Created {} out of {} vehicles".format(i, len(lists[ApiListNames.vehicles].list)))
        vehicle_in_db = Vehicle(
            ingame_id=vehicle.id,
            name=vehicle.name,
            vehicle_class=VehicleClass.objects.get(name=vehicle.vehicle_class.name)
        )
        vehicle_in_db.save(True)
        for livery in vehicle.liveries.list:
            Livery(
                name=livery.name,
                id_for_vehicle=livery.id,
                vehicle=vehicle_in_db
            ).save(True)
