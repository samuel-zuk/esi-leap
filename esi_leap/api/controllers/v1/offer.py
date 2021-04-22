#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime
import http.client as http_client
from oslo_utils import uuidutils
import pecan
from pecan import rest
import wsme
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from esi_leap.api.controllers import base
from esi_leap.api.controllers import types
from esi_leap.api.controllers.v1 import lease
from esi_leap.api.controllers.v1 import utils
from esi_leap.common import exception
from esi_leap.common import policy
from esi_leap.common import statuses
import esi_leap.conf
from esi_leap.objects import lease as lease_obj
from esi_leap.objects import offer as offer_obj

CONF = esi_leap.conf.CONF


class Offer(base.ESILEAPBase):

    name = wsme.wsattr(wtypes.text)
    uuid = wsme.wsattr(wtypes.text, readonly=True)
    project_id = wsme.wsattr(wtypes.text, readonly=True)
    resource_type = wsme.wsattr(wtypes.text)
    resource_uuid = wsme.wsattr(wtypes.text, mandatory=True)
    start_time = wsme.wsattr(datetime.datetime)
    end_time = wsme.wsattr(datetime.datetime)
    status = wsme.wsattr(wtypes.text, readonly=True)
    properties = {wtypes.text: types.jsontype}
    availabilities = wsme.wsattr([[datetime.datetime]], readonly=True)

    def __init__(self, **kwargs):

        self.fields = offer_obj.Offer.fields
        for field in self.fields:
            setattr(self, field, kwargs.get(field, wtypes.Unset))

        setattr(self, 'availabilities', kwargs.get('availabilities',
                                                   wtypes.Unset))


class OfferCollection(types.Collection):
    offers = [Offer]

    def __init__(self, **kwargs):
        self._type = 'offers'


class OffersController(rest.RestController):

    _custom_actions = {
        'claim': ['POST']
    }

    @wsme_pecan.wsexpose(Offer, wtypes.text)
    def get_one(self, offer_id):
        request = pecan.request.context
        cdict = request.to_policy_values()
        policy.authorize('esi_leap:offer:get', cdict, cdict)

        o_object = utils.get_offer(offer_id)
        o = OffersController._add_offer_availabilities(o_object)
        return Offer(**o)

    @wsme_pecan.wsexpose(OfferCollection, wtypes.text, wtypes.text,
                         wtypes.text, datetime.datetime, datetime.datetime,
                         datetime.datetime, datetime.datetime,
                         wtypes.text)
    def get_all(self, project_id=None, resource_type=None,
                resource_uuid=None, start_time=None, end_time=None,
                available_start_time=None, available_end_time=None,
                status=None):

        request = pecan.request.context

        cdict = request.to_policy_values()
        policy.authorize('esi_leap:offer:get', cdict, cdict)

        if (start_time and end_time is None) or\
           (end_time and start_time is None):
            raise exception.InvalidTimeAPICommand(resource='an offer',
                                                  start_time=str(start_time),
                                                  end_time=str(end_time))

        if start_time and end_time and\
           end_time <= start_time:
            raise exception.InvalidTimeAPICommand(resource='an offer',
                                                  start_time=str(start_time),
                                                  end_time=str(end_time))

        if (available_start_time and available_end_time is None) or\
           (available_end_time and available_start_time is None):
            raise exception.InvalidAvailabilityAPICommand(
                a_start=str(start_time),
                a_end=str(end_time))

        if available_start_time and available_end_time and\
                available_end_time <= available_start_time:
            raise exception.InvalidAvailabilityAPICommand(
                a_start=available_start_time,
                a_end=available_end_time)

        if status is None:
            status = statuses.AVAILABLE
        elif status == 'any':
            status = None

        possible_filters = {
            'project_id': project_id,
            'resource_type': resource_type,
            'resource_uuid': resource_uuid,
            'status': status,
            'start_time': start_time,
            'end_time': end_time,
            'available_start_time': available_start_time,
            'available_end_time': available_end_time,
        }

        filters = {}
        for k, v in possible_filters.items():
            if v is not None:
                filters[k] = v

        offer_collection = OfferCollection()
        offers = offer_obj.Offer.get_all(filters, request)

        offer_collection.offers = [
            Offer(**OffersController._add_offer_availabilities(o))
            for o in offers]
        return offer_collection

    @wsme_pecan.wsexpose(Offer, body=Offer, status_code=http_client.CREATED)
    def post(self, new_offer):
        request = pecan.request.context
        cdict = request.to_policy_values()
        policy.authorize('esi_leap:offer:create', cdict, cdict)

        offer_dict = new_offer.to_dict()
        offer_dict['project_id'] = request.project_id
        offer_dict['uuid'] = uuidutils.generate_uuid()
        if 'resource_type' not in offer_dict:
            offer_dict['resource_type'] = CONF.api.default_resource_type

        utils.check_resource_admin(cdict,
                                   offer_dict.get('resource_type'),
                                   offer_dict.get('resource_uuid'),
                                   offer_dict.get('project_id'))

        if 'start_time' not in offer_dict:
            offer_dict['start_time'] = datetime.datetime.now()
        if 'end_time' not in offer_dict:
            offer_dict['end_time'] = datetime.datetime.max

        if offer_dict['start_time'] >= offer_dict['end_time']:
            raise exception.\
                InvalidTimeRange(resource="an offer",
                                 start_time=str(offer_dict['start_time']),
                                 end_time=str(offer_dict['end_time']))

        o = offer_obj.Offer(**offer_dict)
        o.create()
        return Offer(**OffersController._add_offer_availabilities(o))

    @wsme_pecan.wsexpose(Offer, wtypes.text)
    def delete(self, offer_id):
        request = pecan.request.context
        cdict = request.to_policy_values()
        policy.authorize('esi_leap:offer:delete', cdict, cdict)

        o_object = utils.get_offer_authorized(offer_id,
                                              cdict,
                                              statuses.AVAILABLE)

        o_object.cancel()

    @wsme_pecan.wsexpose(lease.Lease, wtypes.text, body=lease.Lease,
                         status_code=http_client.CREATED)
    def claim(self, offer_uuid, new_lease):
        request = pecan.request.context
        cdict = request.to_policy_values()
        policy.authorize('esi_leap:offer:claim', cdict, cdict)

        offer = utils.get_offer(offer_uuid, statuses.AVAILABLE)

        lease_dict = new_lease.to_dict()
        lease_dict['project_id'] = request.project_id
        lease_dict['uuid'] = uuidutils.generate_uuid()
        lease_dict['offer_uuid'] = offer_uuid
        lease_dict['resource_type'] = offer.resource_type
        lease_dict['resource_uuid'] = offer.resource_uuid
        lease_dict['owner_id'] = offer.project_id

        if 'start_time' not in lease_dict:
            lease_dict['start_time'] = datetime.datetime.now()

        if 'end_time' not in lease_dict:
            q = offer.get_first_availability(
                lease_dict['start_time'])
            if q is None:
                lease_dict['end_time'] = offer.end_time
            else:
                lease_dict['end_time'] = q.start_time

        new_lease = lease_obj.Lease(**lease_dict)
        new_lease.create(request)
        return lease.Lease(**new_lease.to_dict())

    @staticmethod
    def _add_offer_availabilities(o):
        availabilities = o.get_availabilities()
        o = o.to_dict()
        o['availabilities'] = availabilities
        return o
