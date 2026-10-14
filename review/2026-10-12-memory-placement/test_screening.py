"""Fake host counters only; importing the assessment never connects to a server."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('memory_screening',Path(__file__).with_name('check_oracle.py'))
screening = importlib.util.module_from_spec(spec);spec.loader.exec_module(screening)


class ScreeningChecks(unittest.TestCase):
    def test_screen_is_not_production_or_billing_approval_and_never_echoes_host_details(self):
        observed = dict(read_only=True,memory_bytes=dict(MemTotal=2**30,MemAvailable=2**29),
            disk_bytes=dict(total=2**32,free=2**31),
            runtimes=dict(system=dict(modules=dict(sqlcipher3=True,pysqlcipher3=False,cryptography=True))),
            mobile_service=dict(ActiveState='active'),private_canary='SYNTHETIC_PRIVATE_HOST')
        report = screening.assess(observed)
        self.assertTrue(all(report['checks'].values()))
        for flag in ('production_ready','billing_eligibility_verified','linux_encrypted_engine_qualified',
                     'protected_key_custody_configured','remote_runtime_changed','private_memory_or_keys_transferred'):
            self.assertIs(report[flag],False)
        self.assertNotIn('SYNTHETIC_PRIVATE_HOST',str(report))
        low = copy.deepcopy(observed);low['memory_bytes']['MemAvailable']=0;low['disk_bytes']['free']=0
        low['runtimes']['system']['modules']['sqlcipher3']=False
        result = screening.assess(low)['checks']
        self.assertFalse(result['memory_screen_256_mib']);self.assertFalse(result['disk_screen_1_gib'])
        self.assertFalse(result['system_sqlcipher_candidate'])
        for bad in (-1,True,'999',None):
            malformed = copy.deepcopy(observed);malformed['disk_bytes']['free']=bad
            with self.assertRaises(ValueError):screening.assess(malformed)
        malformed = copy.deepcopy(observed);malformed['disk_bytes']['free']=2**33
        with self.assertRaises(ValueError):screening.assess(malformed)
        malformed = copy.deepcopy(observed);malformed['read_only']=1
        with self.assertRaises(ValueError):screening.assess(malformed)
        compile(screening.PROGRAM,'remote-read-only','exec')


if __name__=='__main__':unittest.main()
