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

import mock
import pecan
import pecan.testing

from esi_leap.api import app
import esi_leap.conf
from esi_leap.tests import base


CONF = esi_leap.conf.CONF
PATH_PREFIX = '/v1'


class APITestCase(base.DBTestCase):

    def setUp(self):
        super(APITestCase, self).setUp()

        CONF.set_override("auth_enable", False,
                          group='pecan')

        self.app = pecan.testing.load_test_app(
            dict(app.get_pecan_config())
        )

        self.patch_context = mock.patch(
            'oslo_context.context.RequestContext.from_environ'
        )
        self.mock_context = self.patch_context.start()
        self.mock_context.return_value = self.context

    # borrowed from Ironic
    def get_json(self, path, expect_errors=False, headers=None,
                 extra_environ=None, q=None, path_prefix=PATH_PREFIX,
                 **params):
        """Sends simulated HTTP GET request to Pecan test app.

        :param path: url path of target service
        :param expect_errors: Boolean value;whether an error is expected based
                              on request
        :param headers: a dictionary of headers to send along with the request
        :param extra_environ: a dictionary of environ variables to send along
                              with the request
        :param q: list of queries consisting of: field, value, op, and type
                  keys
        :param path_prefix: prefix of the url path
        :param params: content for wsgi.input of request
        """
        q = q if q is not None else []
        full_path = path_prefix + path
        query_params = {'q.field': [],
                        'q.value': [],
                        'q.op': [],
                        }
        for query in q:
            for name in ['field', 'op', 'value']:
                query_params['q.%s' % name].append(query.get(name, ''))
        all_params = {}
        all_params.update(params)
        if q:
            all_params.update(query_params)
        print('GET: %s %r' % (full_path, all_params))
        response = self.app.get(full_path,
                                params=all_params,
                                headers=headers,
                                extra_environ=extra_environ,
                                expect_errors=expect_errors)
        if not expect_errors:
            response = response.json
        print('GOT:%s' % response)
        return response
