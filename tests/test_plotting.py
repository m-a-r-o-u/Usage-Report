from __future__ import annotations
import sys, types, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from usage_report.plotting import create_donut_plot


def _setup_matplotlib(monkeypatch):
    palette = [f"c{i}" for i in range(5)]
    pie_info = {}

    def pie(values, *, labels=None, colors=None, **kwargs):
        pie_info['labels'] = labels
        pie_info['colors'] = colors
        return [], [], []

    class DummyPyplot:
        def figure(self, *a, **kw):
            pass

        def pie(self, *a, **kw):
            return pie(*a, **kw)

        def Circle(self, *a, **kw):
            return object()

        def gca(self):
            class Ax:
                def add_artist(self, *a, **k):
                    pass
            return Ax()

        def title(self, *a, **kw):
            pass

        def axis(self, *a, **kw):
            pass

        def savefig(self, *a, **kw):
            pass

        def close(self, *a, **kw):
            pass

    dummy_pyplot = DummyPyplot()
    dummy_matplotlib = types.SimpleNamespace(
        use=lambda *a, **kw: None,
        cm=types.SimpleNamespace(tab20=types.SimpleNamespace(colors=tuple(palette))),
        pyplot=dummy_pyplot,
    )

    monkeypatch.setitem(sys.modules, 'matplotlib', dummy_matplotlib)
    monkeypatch.setitem(sys.modules, 'matplotlib.pyplot', dummy_pyplot)
    return palette, pie_info


def test_color_order(monkeypatch):
    palette, pie_info = _setup_matplotlib(monkeypatch)
    rows = [
        {'kennung': 'g1', 'gpu_hours': 100},
        {'kennung': 'g2', 'gpu_hours': 70},
        {'kennung': 'g3', 'gpu_hours': 5},
        {'kennung': 'g4', 'gpu_hours': 60},
    ]
    create_donut_plot(rows, 'gpu_hours')

    assert pie_info['labels'] == ['g1', 'g2', 'Others']
    colors = pie_info['colors']
    assert colors[pie_info['labels'].index('g1')] == palette[0]
    assert colors[pie_info['labels'].index('g2')] == palette[1]
    assert colors[pie_info['labels'].index('Others')] == 'gray'
