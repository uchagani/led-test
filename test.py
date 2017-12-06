import code

from leds_service import *
leds_service = LedsService()

code.interact(local=dict(globals(), **locals()))


#leds_service.start_animation(LedsService.State.listening)
