###############
#TODO for phonetrack
- implement a homeassistant integration setup flow
- add a reconfigure setup flow 
- improve the code so that if nextcloud/phonetrack server is unavailable it tries to reconnect on a configurable interval. default 300s
- check the homeassistant documentation regarding device-trackers https://www.home-assistant.io/integrations/device_tracker and implement the needed changes the phonetrak gets compatible with future versions

so from "Legacy device tracker" to "Position trackers"


Some integrations provide an older device tracker model which do not have the tracking_type or in_zones state attributes. These device trackers are scheduled for removal in the first half of 2027.
