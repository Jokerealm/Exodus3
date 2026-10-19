"""Synthetic banks only; these checks never access a game's live bank."""
import os
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bank_model import BankDocument,encode_integer,field_name
from sc2_cipher import encode_sequence

HANDLE='5-S2-1-1234567'

def fixture(values):
    data=('<Bank version="1"><Section name="R"><Key name="R"><Value string="'+
          encode_sequence(values)+'"/></Key></Section><Section name="FUTURE">'+
          '<Key name="keep"><Value string="unknown data"/></Key></Section></Bank>').encode()
    bank=BankDocument(data,handle=HANDLE)
    bank.paired('RS','RS',sum(values))
    return BankDocument(bank.to_bytes(),handle=HANDLE)

class ResourcesTest(unittest.TestCase):
    def test_legacy_noop_is_byte_identical(self):
        bank=fixture(list(range(1,13)))
        bank.set_resources(list(bank.resources))
        self.assertEqual(bank.to_bytes(),bank.original)

    def test_extend_legacy_keeps_old_ciphertext_and_other_keys(self):
        bank=fixture(list(range(1,13)))
        old=bank.value('R','R')[1].split()
        bank.set_resources(list(range(1,13))+[101,202,303])
        reread=BankDocument(bank.to_bytes(),handle=HANDLE)
        self.assertEqual(reread.resources,list(range(1,13))+[101,202,303])
        self.assertEqual(reread.value('R','R')[1].split()[:12],old)
        self.assertEqual(reread.get_paired('RS','RS'),684)
        self.assertEqual(reread.value(field_name(HANDLE,'RS'),field_name(HANDLE,'RS-en')),
                         ('string',encode_integer(684,HANDLE,'RS')))
        self.assertEqual(reread.value('FUTURE','keep'),('string','unknown data'))
        self.assertEqual(len(bank.changes),3)

    def test_each_new_mineral_updates_sum_and_only_its_token(self):
        for index in (12,13,14):
            with self.subTest(index=index):
                bank=fixture([10]*15);old=bank.value('R','R')[1].split()
                values=list(bank.resources);values[index]=99;bank.set_resources(values)
                self.assertEqual(bank.get_paired('RS','RS'),239)
                self.assertEqual([i for i,(a,b) in enumerate(zip(old,bank.value('R','R')[1].split())) if a!=b],[index])

    def test_all_new_minerals_enforce_bounds(self):
        for index in (12,13,14):
            for invalid in (-1,90_000_001):
                with self.subTest(index=index,invalid=invalid):
                    bank=fixture([0]*15);values=list(bank.resources);values[index]=invalid
                    with self.assertRaises(ValueError):bank.set_resources(values)
                    self.assertEqual(bank.to_bytes(),bank.original)

    def test_maximum_all_fifteen(self):
        bank=fixture([0]*15);bank.set_resources([90_000_000]*15)
        self.assertEqual(bank.get_paired('RS','RS'),1_350_000_000)

    def test_no_truncation_or_arbitrary_extension(self):
        for initial,target in ((15,12),(12,13),(12,16),(16,15)):
            with self.subTest(initial=initial,target=target):
                bank=fixture([1]*initial)
                with self.assertRaises(ValueError):bank.set_resources([2]*target)

    def test_future_tail_is_preserved_and_included_in_sum(self):
        bank=fixture([10]*15+[123]);values=list(bank.resources);values[12]=99
        bank.set_resources(values)
        self.assertEqual(bank.resources[-1],123)
        self.assertEqual(bank.get_paired('RS','RS'),362)

    def test_legacy_edit_stays_twelve(self):
        bank=fixture([10]*12);values=list(bank.resources);values[0]=99;bank.set_resources(values)
        self.assertEqual(len(bank.resources),12)
        self.assertEqual(bank.get_paired('RS','RS'),209)

try:
    from PySide6.QtWidgets import QApplication
    from app import EditorWindow
except ImportError:
    QApplication=None

@unittest.skipIf(QApplication is None,'PySide6 is not installed')
class ResourceGuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.window=EditorWindow(state_dir=self.temp.name)
        self.window.autosave.setChecked(False)

    def tearDown(self):
        self.window.timer.stop();self.window.deleteLater();self.temp.cleanup()

    def test_opt_in_preview_reset_and_old_draft(self):
        bank=fixture([10]*12)
        self.window.load_document(bank)
        self.assertEqual(len(self.window.resource_edits),15)
        self.assertFalse(self.window.resource_edits[12].isEnabled())
        self.assertEqual(self.window.build_document().to_bytes(),bank.original)
        self.window.test_resources.setChecked(True)
        for i,n in enumerate((101,202,303),12):self.window.resource_edits[i].setText(str(n))
        updated=self.window.build_document()
        self.assertEqual(updated.resources[-3:],[101,202,303])
        self.assertEqual(updated.get_paired('RS','RS'),726)
        self.window.reset()
        self.assertFalse(self.window.test_resources.isChecked())
        self.assertEqual(self.window.build_document().to_bytes(),bank.original)

    def test_existing_fifteen_and_future_tail_survive_gui(self):
        for count in (15,16):
            with self.subTest(count=count):
                bank=fixture([10]*count);self.window.load_document(bank)
                self.assertTrue(self.window.test_resources.isChecked())
                self.assertFalse(self.window.test_resources.isEnabled())
                self.assertEqual(self.window.build_document().to_bytes(),bank.original)
                self.window.resource_edits[14].setText('99')
                updated=self.window.build_document()
                self.assertEqual(len(updated.resources),count)
                self.assertEqual(updated.get_paired('RS','RS'),count*10+89)

    def test_draft_restores_new_minerals_and_accepts_old_format(self):
        path=Path(self.temp.name)/'EX3Data.SC2Bank'
        path.write_bytes(fixture([10]*12).original)
        self.window.load_document(BankDocument.load(path))
        self.window.test_resources.setChecked(True)
        self.window.resource_edits[12].setText('123')
        self.window.resource_edits[13].setText('234')
        self.window.resource_edits[14].setText('345')
        self.window.save_draft();self.window.reset();self.window.restore_draft()
        self.assertTrue(self.window.test_resources.isChecked())
        self.assertEqual(self.window.build_document().resources[-3:],[123,234,345])
        state=json.loads(self.window.draft_path.read_text(encoding='utf-8'))
        state.pop('test_resources');state['resources']=state['resources'][:12]
        self.window.draft_path.write_text(json.dumps(state),encoding='utf-8')
        self.window.restore_draft()
        self.assertFalse(self.window.test_resources.isChecked())
        self.assertEqual(len(self.window.build_document().resources),12)

    def test_export_preserves_source_and_creates_backup(self):
        source=Path(self.temp.name)/'source.SC2Bank'
        source.write_bytes(fixture([10]*12).original)
        self.window.load_document(BankDocument.load(source))
        self.window.test_resources.setChecked(True)
        self.window.resource_edits[14].setText('123')
        updated=self.window.build_document();target=Path(self.temp.name)/'export.SC2Bank'
        backup=updated.save(target)
        self.assertEqual(backup.read_bytes(),source.read_bytes())
        self.assertEqual(BankDocument.load(target).resources,[10]*12+[0,0,123])
        self.assertEqual(len(BankDocument.load(source).resources),12)

if __name__=='__main__':unittest.main()
