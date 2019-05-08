"""
A view (URL=/sql_provider) allowing to enabled/disable a SQL spy that runs an "EXPLAIN ANALYZE" on
every SELECT query going through SQLAlchemy.
"""
import logging
import re
from threading import Lock
from typing import Any, Mapping, Set

import pyramid.request
import sqlalchemy.engine
import sqlalchemy.event

from c2cwsgiutils import _utils, auth, broadcast

LOG = logging.getLogger(__name__)
repository = None


class _Repository:
    def __init__(self) -> None:
        super().__init__()
        self._lock = Lock()
        self._repo: Set[str] = set()

    def profile(self, conn: sqlalchemy.engine.Connection, _cursor: Any, statement: str, parameters: Any,
                _context: Any, _executemany: Any) -> None:
        if statement.startswith("SELECT ") and LOG.isEnabledFor(logging.INFO):
            do_it = False
            with self._lock:
                if statement not in self._repo:
                    do_it = True
                    self._repo.add(statement)
            if do_it:
                try:
                    LOG.info("statement:\n%s", _indent(_beautify_sql(statement)))
                    LOG.info("parameters: %s", repr(parameters))
                    output = '\n  '.join([
                        row[0] for row in conn.engine.execute("EXPLAIN ANALYZE " + statement, parameters)
                    ])
                    LOG.info(output)
                except Exception:
                    pass


def _sql_profiler_view(request: pyramid.request.Request) -> Mapping[str, Any]:
    global repository
    auth.auth_view(request)
    enable = request.params.get('enable')
    if enable is not None:
        broadcast.broadcast('c2c_sql_profiler', params={'enable': enable}, expect_answers=True)
    return {'status': 200, 'enabled': repository is not None}


def _setup_profiler(enable: str) -> None:
    global repository
    if _utils.config_bool(enable):
        if repository is None:
            LOG.warning("Enabling the SQL profiler")
            repository = _Repository()
            sqlalchemy.event.listen(sqlalchemy.engine.Engine, "before_cursor_execute",
                                    repository.profile)
    else:
        if repository is not None:
            LOG.warning("Disabling the SQL profiler")
            sqlalchemy.event.remove(sqlalchemy.engine.Engine, "before_cursor_execute",
                                    repository.profile)
            repository = None


def _beautify_sql(statement: str) -> str:
    statement = re.sub(r'SELECT [^\n]*\n', 'SELECT ...\n', statement)
    statement = re.sub(r' ((?:LEFT )?(?:OUTER )?JOIN )', r'\n\1', statement)
    statement = re.sub(r' ON ', r'\n  ON ', statement)
    statement = re.sub(r' GROUP BY ', r'\nGROUP BY ', statement)
    statement = re.sub(r' ORDER BY ', r'\nORDER BY ', statement)
    return statement


def _indent(statement: str, indent: str = '  ') -> str:
    return indent + ("\n" + indent).join(statement.split('\n'))


def init(config: pyramid.config.Configurator) -> None:
    """
    Install a pyramid  event handler that adds the request information
    """
    broadcast.subscribe('c2c_sql_profiler', _setup_profiler)

    config.add_route("c2c_sql_profiler", _utils.get_base_path(config) + r"/sql_profiler",
                     request_method="GET")
    config.add_view(_sql_profiler_view, route_name="c2c_sql_profiler", renderer="fast_json", http_cache=0)
    LOG.info("Enabled the /sql_profiler API")