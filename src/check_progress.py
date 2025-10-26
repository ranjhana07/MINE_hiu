from mine_armour_dashboard import data_manager
import pprint

rf = data_manager.get_rfid_data()
print('Checkpoint progress:')
pp = pprint.PrettyPrinter(indent=2)
pp.pprint(rf.get('checkpoint_progress'))

print('\nLatest tag/station:')
print(rf.get('latest_tag'), rf.get('latest_station'))
