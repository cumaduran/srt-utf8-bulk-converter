import codecs
import tempfile
import unittest
from pathlib import Path

from srtstudio.core import Options, build_plan, convert_batch, convert_one, decode_subtitle


TEXT = 'Sınavı çok erken. Şimdi öyle mi? İğne, Çarşamba, ıslık!\r\n2\r\n00:00:01,200 --> 00:00:03,400\r\nGüzel şeyler.\r\n'


class EncodingTests(unittest.TestCase):
    def test_cp1254_to_utf8(self):
        with tempfile.TemporaryDirectory() as work:
            file = Path(work) / 'turkish.srt'
            file.write_bytes(TEXT.encode('cp1254'))
            results = convert_batch(Options((file,)))
            self.assertEqual(results[0].status, 'done')
            self.assertEqual(results[0].encoding, 'Windows-1254')
            actual = (Path(work) / 'utf8' / 'turkish.srt').read_bytes()
            self.assertEqual(actual, TEXT.encode('utf-8'))
            self.assertFalse(actual.startswith(codecs.BOM_UTF8))

    def test_existing_utf8_is_not_misdecoded(self):
        data = TEXT.encode('utf-8')
        text, encoding = decode_subtitle(data)
        self.assertEqual(text, TEXT)
        self.assertEqual(encoding, 'UTF-8')

    def test_utf8_bom_removed(self):
        with tempfile.TemporaryDirectory() as work:
            file = Path(work) / 'bom.srt'
            file.write_bytes(codecs.BOM_UTF8 + TEXT.encode('utf-8'))
            result = convert_batch(Options((file,)))[0]
            self.assertEqual(result.encoding, 'UTF-8 BOM')
            self.assertEqual((Path(work) / 'utf8' / 'bom.srt').read_bytes(), TEXT.encode('utf-8'))

    def test_utf16_bom_supported(self):
        text, encoding = decode_subtitle(TEXT.encode('utf-16'))
        self.assertEqual(text, TEXT)
        self.assertEqual(encoding, 'UTF-16 BOM')

    def test_undecodable_text_fails_safely(self):
        with tempfile.TemporaryDirectory() as work:
            file = Path(work) / 'bad.srt'
            file.write_bytes(b'abc\x81\xff')
            result = convert_batch(Options((file,)))[0]
            self.assertEqual(result.status, 'failed')
            self.assertFalse((Path(work) / 'utf8' / 'bad.srt').exists())

    def test_replacement_character_warns(self):
        with tempfile.TemporaryDirectory() as work:
            file = Path(work) / 'broken.srt'
            file.write_text('S�nav�', encoding='utf-8')
            result = convert_batch(Options((file,)))[0]
            self.assertEqual(result.status, 'warning')
            self.assertIn('�', result.message)

    def test_refuses_binary_without_bom(self):
        with self.assertRaises(UnicodeError):
            decode_subtitle(b'a\x00b\x00')


class BatchTests(unittest.TestCase):
    def test_folder_generates_utf8_neighbor_and_keeps_sources(self):
        with tempfile.TemporaryDirectory() as work:
            folder = Path(work) / 'source'
            sub = folder / 'season1'
            sub.mkdir(parents=True)
            (sub / 'episode.SRT').write_bytes(TEXT.encode('cp1254'))
            results = convert_batch(Options((folder,)))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].status, 'done')
            self.assertEqual((folder / 'utf8' / 'season1' / 'episode.SRT').read_bytes(), TEXT.encode('utf-8'))
            self.assertEqual((sub / 'episode.SRT').read_bytes(), TEXT.encode('cp1254'))
            self.assertEqual(len(build_plan(Options((folder,)))), 1)  # avoid re-reading output

    def test_flat_no_recursive(self):
        with tempfile.TemporaryDirectory() as work:
            folder = Path(work)
            (folder / 'top.srt').write_bytes(b'ok')
            (folder / 'sub').mkdir()
            (folder / 'sub' / 'nested.srt').write_bytes(b'ok')
            plan = build_plan(Options((folder,), recursive=False, preserve_structure=False))
            self.assertEqual(len(plan), 1)
            self.assertEqual(plan[0].source.name, 'top.srt')

    def test_multiple_roots_namespaced_in_custom_output(self):
        with tempfile.TemporaryDirectory() as work:
            base = Path(work)
            one = base / 'one'
            two = base / 'two'
            one.mkdir()
            two.mkdir()
            (one / 'ep.srt').write_bytes(b'first')
            (two / 'ep.srt').write_bytes(b'second')
            target = base / 'export'
            results = convert_batch(Options((one, two), target))
            self.assertEqual(len(results), 2)
            self.assertEqual((target / 'one' / 'ep.srt').read_bytes(), b'first')
            self.assertEqual((target / 'two' / 'ep.srt').read_bytes(), b'second')

    def test_existing_output_is_not_overwritten_unless_opted_in(self):
        with tempfile.TemporaryDirectory() as work:
            file = Path(work) / 'sub.srt'
            file.write_bytes(b'new')
            output = Path(work) / 'utf8'
            output.mkdir()
            (output / 'sub.srt').write_bytes(b'keep')
            result = convert_batch(Options((file,)))[0]
            self.assertEqual(result.status, 'skipped')
            self.assertEqual((output / 'sub.srt').read_bytes(), b'keep')
            convert_batch(Options((file,), overwrite=True))
            self.assertEqual((output / 'sub.srt').read_bytes(), b'new')

    def test_duplicate_input_file_is_processed_once(self):
        with tempfile.TemporaryDirectory() as work:
            file = Path(work) / 'a.srt'
            file.write_bytes(b'hi')
            jobs = build_plan(Options((file, file, Path(work))))
            self.assertEqual(len(jobs), 1)

    def test_collision_between_same_named_sources_is_skipped(self):
        with tempfile.TemporaryDirectory() as work:
            base = Path(work)
            (base / 'one').mkdir()
            (base / 'two').mkdir()
            a = base / 'one' / 'x.srt'
            b = base / 'two' / 'x.srt'
            a.write_bytes(b'a')
            b.write_bytes(b'b')
            results = convert_batch(Options((a, b), base / 'out'))
            self.assertEqual([r.status for r in results], ['done', 'skipped'])
            self.assertEqual((base / 'out' / 'x.srt').read_bytes(), b'a')

    def test_nested_custom_output_excluded(self):
        with tempfile.TemporaryDirectory() as work:
            src = Path(work)
            (src / 'episode.srt').write_bytes(b'hi')
            target = src / 'output'
            target.mkdir()
            (target / 'old.srt').write_bytes(b'old')
            plan = build_plan(Options((src,), target))
            self.assertEqual(len(plan), 1)

    def test_cancel_stops_between_files(self):
        with tempfile.TemporaryDirectory() as work:
            base = Path(work)
            for index in range(5):
                (base / f'{index}.srt').write_bytes(b'abc')
            processed = []
            results = convert_batch(Options((base,)),
                on_result=lambda r, i, n: processed.append(r),
                should_cancel=lambda: len(processed) >= 2)
            self.assertEqual(len(results), 2)

    def test_srt_sample_from_naruto_21(self):
        sample = Path('/mnt/data/ANKANRT021-b.srt')
        if not sample.exists():
            self.skipTest('Optional user-supplied sample unavailable on CI')
        with tempfile.TemporaryDirectory() as work:
            dest = Path(work) / '21.srt'
            dest.write_bytes(sample.read_bytes())
            result = convert_batch(Options((dest,)))[0]
            self.assertEqual(result.encoding, 'Windows-1254')
            result_text = (Path(work) / 'utf8' / '21.srt').read_text(encoding='utf-8')
            self.assertIn('Peşimde bilmediğim', result_text)


if __name__ == '__main__':
    unittest.main()
