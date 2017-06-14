"""
Implement parts of the Prometheus Pushgateway protocol, as defined here:
https://github.com/prometheus/pushgateway
"""
import requests


class PushgatewayGroupPublisher(object):
    def __init__(self, base_url, job, instance=None):
        if not base_url.endswith('/'):
            base_url += '/'
        self._url = "%smetrics/job/%s" % (base_url, job)
        if instance is not None:
            self._url += '/instance/' + instance
        self._reset()

    def add(self, metric_name, metric_value, metric_type='gauge', metric_labels=None):
        if metric_name in self._types:
            if self._types[metric_name] != metric_type:
                raise ValueError("Cannot change the type of a given metric")
        else:
            self._types[metric_name] = metric_type
            self._to_send += '# TYPE %s %s\n' % (metric_name, metric_type)
        self._to_send += metric_name
        if metric_labels is not None:
            self._to_send += '{' + ', '.join('%s="%s"' % (k, v) for k, v in metric_labels.items()) + '}'
        self._to_send += ' %s\n' % metric_value

    def commit(self):
        requests.put(self._url, data=self._to_send).raise_for_status()
        self._reset()

    def _reset(self):
        self._to_send = ''
        self._types = {}

    def __str__(self):
        return self._url + ' ->\n' + self._to_send