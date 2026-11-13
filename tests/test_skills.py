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
    def test_pale_yellow_skill_packages_match(self):
        codex=ROOT/'.agents/skills/pale-yellow-reel'
        claude=ROOT/'.claude/skills/pale-yellow-reel'
        files=['SKILL.md','agents/openai.yaml','assets/style.json','scripts/render.py']
        for relative in files:
            with self.subTest(file=relative):
                self.assertEqual((codex/relative).read_bytes(),(claude/relative).read_bytes())
        # Exact reference assets must remain local, outside the public package.
        for folder in [codex,claude]:
            self.assertFalse((folder/'assets/title.png').exists())
            self.assertFalse((folder/'assets/audio.m4a').exists())


if __name__=='__main__':unittest.main()
