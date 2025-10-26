from mine_armour_dashboard import data_manager
import pprint

print('Simulating first scan for c7761005 at A1')
data_manager.add_rfid_data({'station_id':'A1', 'tag_id':'c7761005'})
print('Simulating second scan for c7761005 at A2')
data_manager.add_rfid_data({'station_id':'A2', 'tag_id':'c7761005'})

rfid = data_manager.get_rfid_data()
print('\nCheckpoint progress:')
pp = pprint.PrettyPrinter(indent=2)
pp.pprint(rfid.get('checkpoint_progress'))

print('\nLatest scans list:')
pp.pprint(list(rfid.get('uid_scans')))
