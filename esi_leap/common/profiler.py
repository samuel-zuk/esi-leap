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

from oslo_context.context import RequestContext
from oslo_log import log as logging
from osprofiler import initializer
from osprofiler import profiler

import esi_leap.conf

CONF = esi_leap.conf.CONF

LOG = logging.getLogger(__name__)

def setup(name, host='0.0.0.0'):
    admin_ctx = RequestContext(auth_token=None,
                               project_id=None,
                               overwrite=False)
    initializer.init_from_conf(conf=CONF,
                               context=admin_ctx.to_dict(),
                               project='esi_leap',
                               service=name,
                               host=host)
    LOG.info('OSProfiler is enabled. Trace is generated using the HMAC key(s) '
             'specified in the [profiler]/hmac_keys section of esi_leap.conf. '
             'To disable, set the value of [profiler]/enabled equal to False.')


def trace_cls(name, **kwargs):
    def decorator(cls):
        if CONF.profiler.enabled:
            log.debug('OSProfiler: wrapping class %s' % cls.__name__)
            trace_decorator = profiler.trace_cls(name, kwargs)
            return trace_decorator(cls)
        return cls

    return decorator
