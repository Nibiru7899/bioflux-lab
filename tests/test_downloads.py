import pytest

from bioflux.downloads import fetch


@pytest.mark.parametrize('url', ['http://bigg.ucsd.edu/static/models/e_coli_core.json',
                                 'https://unreviewed.example/model.json',
                                 'https://bigg.ucsd.edu.unreviewed.example/model.json',
                                 'file:///tmp/model.json'])
def test_unapproved_sources_are_rejected_before_network(url, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('A rejected URL reached the network')
    monkeypatch.setattr('requests.Session.get', forbidden)
    with pytest.raises(ValueError, match='not allowlisted'):
        fetch(url)


def test_redirect_destination_is_checked_before_request(monkeypatch):
    class Redirect:
        is_redirect = True
        headers = {'Location': 'https://unreviewed.example/payload'}
        def close(self):
            pass
    calls = []
    def get(self, url, **kwargs):
        calls.append(url)
        return Redirect()
    monkeypatch.setattr('requests.Session.get', get)
    with pytest.raises(ValueError, match='not allowlisted'):
        fetch('https://bigg.ucsd.edu/static/models/e_coli_core.json')
    assert calls == ['https://bigg.ucsd.edu/static/models/e_coli_core.json']
