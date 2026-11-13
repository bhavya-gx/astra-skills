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
    def test_reference_script_skill_copies_match_and_have_their_files(self):
        codex=ROOT/'.agents/skills/reference-script';claude=ROOT/'.claude/skills/reference-script'
        for relative in ['SKILL.md','agents/openai.yaml']:
            with self.subTest(file=relative):
                self.assertEqual((codex/relative).read_bytes(),(claude/relative).read_bytes())
        text=(codex/'SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(text.startswith('---\nname: reference-script\n'))
        self.assertIn('[CHECK]',text)
        self.assertIn('reference-script skill',(ROOT/'prompts/reference-script.md').read_text(encoding='utf-8'))
        for name in ['facts-interview.md','example-facts.md']:
            self.assertTrue((ROOT/'voice'/name).is_file())
        self.assertIn('fictional',(ROOT/'voice/example-facts.md').read_text(encoding='utf-8'))
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
