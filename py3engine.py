import requests
import threading
import logging
import time
import os

logging.basicConfig(filename=os.path.expanduser('~/.py3engine.log'), filemode='w', level=logging.DEBUG)


class NotificationManager(object):
    def __init__(self):
        self.panel_name_by_func = {}
        self.panel_by_name = {}

    def panel(self, index):
        def decorator_setup_func(func):
            def proxy_func(p_self, a, b):
                if func not in self.panel_name_by_func:
                    panel_instance = func(p_self)
                    service_name = "%s_%s" % (panel_instance.__class__.__name__, index)
                    self.panel_by_name[service_name] = panel_instance
                    self.panel_name_by_func[func] = service_name
                else:
                    service_name = self.panel_name_by_func[func]
                    panel_instance = self.panel_by_name[service_name]

                response = panel_instance.GetResponse()
                response["name"] = service_name
                
                return (index, panel_instance.GetResponse())
            return proxy_func
        return decorator_setup_func

    def DispatchClick(self, evt):
        panel_instance = self.panel_by_name[evt["name"]]
        panel_instance.OnClick()

    def Shutdown(self, evt):
        for _, panel in self.panel_by_name.items():
            panel.Stop()

class TimeoutManager(object):
    def __init__(self, config):
        self.config = config
        self.active_timeout = int(self.config.get("active_timeout_sec", 10))
        self.passive_timeout = int(self.config.get("passive_timeout_sec", 300))
        self.passivation_cycles_count = int(self.config.get("passivation_cycles_count", 18))
        self.active_timeouts_passed = 0
        self.Wakeup()

    def Wakeup(self):
        self.active_timeouts_passed = self.passivation_cycles_count

    def GetWaitTime(self):
        if self.active_timeouts_passed>0:
            self.active_timeouts_passed = self.active_timeouts_passed - 1
            return self.active_timeout
        else:
            return self.passive_timeout

class Success(object):
    def __init__(self, response, retry_timeout):
        self.response = response
        self.retry_timeout = retry_timeout

class WebPane(object):
    def __init__(self):
        self.NewSession()

        self.broken = False
        self.response = {
            "cached_until": time.time()+5,
            "full_text": "No data"
        }
        self.completed = False

        self.thread = threading.Thread(target=lambda: self._ThreadProc())
        self.thread.daemon = True
        self.thread.start()
    
    def _ThreadProc(self):
         while not self.completed:
            try:
                query_result = self.Query()
                self.response = query_result.response
                if "cached_until" not in self.response:
                    self.response["cached_until"] = time.time()+5
                time.sleep(query_result.retry_timeout)

            except Exception as e:
                logging.exception("Unable to retrieve notifications")
                time.sleep(10)
    
    def NewSession(self):
        self.session = self._BuildSessionObject()
    

    def GetResponse(self):
        return self.response

    def _BuildSessionObject(self):
        session = requests.Session()
        session.mount("", requests.adapters.HTTPAdapter(max_retries=10))
        return session 

    def OnClick(self):
        pass

    def Stop(self):
        self.completed = True

