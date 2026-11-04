import sys,unittest,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'.agents/skills/mi-sky-investing'
class TestSkill(unittest.TestCase):
  def test_structure(self):
    self.assertTrue((S/'SKILL.md').is_file())
    self.assertTrue((S/'references/core-methodology.md').is_file())
  def test_technical_operation_exists(self):
    self.assertTrue((S/"references/technical-playbook.md").is_file())
    self.assertTrue((S/"scripts/analyze_ohlcv.py").is_file())
    body=(S/"references/technical-playbook.md").read_text(encoding="utf-8")
    for phrase in ("MA5", "MA20", "RVOL20", "520战法", "成交量", "右侧抄底"):
      self.assertIn(phrase,body)
  def test_screening_and_entry_exit_guides(self):
    for file in ("references/stock-selection.md", "references/price-action-and-exits.md", "scripts/screen_watchlist.py"):
      self.assertTrue((S/file).is_file(), file)
    sk=(S/"SKILL.md").read_text(encoding="utf-8")
    for phrase in ("stock-selection.md", "price-action-and-exits.md", "screen_watchlist.py", "1.2.0"):
      self.assertIn(phrase,sk)
  def test_multitimeframe_profile_and_chip_protocol(self):
    self.assertTrue((S/"references/multi-timeframe-and-chips.md").is_file())
    self.assertTrue((S/"scripts/analyze_multitimeframe.py").is_file())
    guide=(S/"references/multi-timeframe-and-chips.md").read_text(encoding="utf-8")
    for word in ("120分钟", "5分钟", "均线粘合", "筹码成本分布", "已完成"):
      self.assertIn(word,guide)
  def test_new_2026_11_04_source_audit_and_theory_boundaries(self):
    idx=(S/"references/source-index.md").read_text(encoding="utf-8")
    self.assertIn("目录中共34个文件",idx)
    for tag in ("C01", "C02"):
      self.assertIn(tag,idx)
    for p in ("references/chanlun-framework.md", "references/unified-decision-framework.md",
              "scripts/chan_segment_check.py"):
      self.assertTrue((S/p).is_file(),p)
    protocol=(S/"references/evidence-protocol.md").read_text(encoding="utf-8")
    self.assertIn("独立",protocol)
    theory=(S/"references/chanlun-framework.md").read_text(encoding="utf-8")
    for phrase in ("ZD", "ZG", "次级别", "首次", "三买", "三卖"):
      self.assertIn(phrase,theory)
    main=(S/"SKILL.md").read_text(encoding="utf-8")
    self.assertIn('version: "1.5.0"',main)
    self.assertIn("chanlun-framework.md",main)
    self.assertIn("unified-decision-framework.md",main)
  def test_new_source_sync_and_strict_chan_checker(self):
    self.assertTrue((S/"references/source-sync-audit-2026-11-04.md").is_file())
    self.assertTrue((S/"scripts/check_chan_setup.py").is_file())
    self.assertTrue((S/"references/unified-decision-framework.md").is_file())
    source=(S/"references/source-index.md").read_text(encoding="utf-8")
    self.assertIn("34个文件",source)
    main=(S/"SKILL.md").read_text(encoding="utf-8")
    self.assertIn("check_chan_setup.py",main)
    self.assertIn("source-sync-audit-2026-11-04.md",main)
  def test_provenance_distinction(self):
    t=(S/'SKILL.md').read_text(encoding='utf-8')
    for tag in ('[作者原意]','[框架推演]','[外部事实]'):
      self.assertIn(tag,t)
  def test_risk_and_no_invented_live_data(self):
    t=(S/'SKILL.md').read_text(encoding='utf-8')
    for phrase in ('不得编造','反证','左侧','右侧','仓位','来源'):
      self.assertIn(phrase,t)
  def test_source_not_duplicated(self):
    s=(S/'references/source-index.md').read_text(encoding='utf-8')
    self.assertIn('不能重复计权',s)
  def test_validator(self):
    p=subprocess.run([sys.executable,str(S/'scripts/validate_skill.py')],capture_output=True,text=True)
    self.assertEqual(p.returncode,0,p.stdout+p.stderr)
if __name__=='__main__':unittest.main()
