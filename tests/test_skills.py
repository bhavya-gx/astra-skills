from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class SkillTests(unittest.TestCase):
    def test_codex_and_claude_skill_copies_match(self):
        codex=(ROOT/'.agents/skills/reel-edit/SKILL.md').read_text(encoding='utf-8')
        claude=(ROOT/'.claude/skills/reel-edit/SKILL.md').read_text(encoding='utf-8')
        self.assertEqual(codex,claude)
    def test_skill_frontmatter(self):
        text=(ROOT/'.agents/skills/reel-edit/SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(text.startswith('---\nname: reel-edit\n'))
        self.assertIn('\ndescription: ',text.split('---')[1])
    def test_first_edit_prompt_names_the_skill(self):
        self.assertIn('reel-edit skill',(ROOT/'prompts/first-edit.md').read_text(encoding='utf-8'))


if __name__=='__main__':unittest.main()
