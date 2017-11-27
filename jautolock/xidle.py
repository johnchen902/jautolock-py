"""get idle time from X server"""
import datetime
import Xlib.display
from Xlib.protocol import rq

__all__ = ['get_idle_time']

EXTNAME = 'MIT-SCREEN-SAVER'

class ScreenSaverQueryInfo(rq.ReplyRequest):
    _request = rq.Struct(rq.Card8('opcode'),
                         rq.Opcode(1),
                         rq.RequestLength(),
                         rq.Drawable('drawable'),
                        )
    _reply = rq.Struct(rq.ReplyCode(),
                       rq.Card8('state'),
                       rq.Card16('sequence_number'),
                       rq.ReplyLength(),
                       rq.Window('saver_window'),
                       rq.Card32('saver_time'),
                       rq.Card32('idle_time'),
                       rq.Card32('events'),
                       rq.Card8('kind'),
                       rq.Pad(7), # spec said 10 but only 7 works
                      )

def screen_saver_query_info(self):
    return ScreenSaverQueryInfo(
        display=self.display,
        opcode=self.display.get_extension_major(EXTNAME),
        drawable=self)

def get_idle_time():
    """get idle time from X server"""
    display = Xlib.display.Display()
    info = display.query_extension(EXTNAME)
    display.display.set_extension_major(EXTNAME, info.major_opcode)
    millis = screen_saver_query_info(display.screen().root).idle_time
    return datetime.timedelta(milliseconds=millis)
