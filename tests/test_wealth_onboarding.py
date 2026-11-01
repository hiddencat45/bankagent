"""First-use onboarding stays optional for browsing and never writes implicitly."""
from copy import deepcopy
import pytest
from bankagent.banking.wealth import PRODUCTS
from test_wealth import FIELDS,ANSWERS


@pytest.fixture
def page(monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication
    from desktop.wealth import WealthPage
    app=QApplication.instance() or QApplication([])
    p=WealthPage();p.interview_events=[];p.interview_requested.connect(lambda:p.interview_events.append('start'))
    p.resize(1000,800);p.show()
    p.set_data(dict(products=PRODUCTS,recommendations=[],profile=None,profile_valid=False,
        orders=[],lots=[],day='2026-11-01',available_minor=500000,holdings_minor=0,frozen_minor=0,waiting_minor=0),('alice','account-a'))
    p.set_available(True);app.processEvents()
    yield p,app
    p.questionnaire.reject();p.close();p.deleteLater();app.processEvents()


def test_first_visit_defer_and_explicit_gate_never_saves(page):
    p,app=page;calls=[];p.requested.connect(lambda *args:calls.append(args))
    assert not p.questionnaire.isVisible() and p.interview_events==['start']
    p.maybe_onboard();app.processEvents()
    assert not p.questionnaire.isVisible() and not calls
    p.set_data(deepcopy(p.data),('alice','account-a2'));p.maybe_onboard()
    assert not p.questionnaire.isVisible()  # Switching this customer's accounts does not nag again.
    p.products.select_buttons[1].click();assert p.products.currentRow()==1
    p.buy_amount.setText('100');p.buy.click();assert p.interview_events==['start','start'] and not calls
    p.compare.click();assert p.interview_events==['start','start','start'] and not calls
    p.edit_profile.click();assert p.questionnaire.isVisible() and not calls


def test_catalog_paging_preserves_product_identity_and_selection(page):
    p,app=page;p.questionnaire.reject();cards=p.products
    assert cards.rowCount()==10 and cards.box.count()==6
    cards.next.click();app.processEvents()
    assert cards.page==1 and cards.box.count()==4
    cards.select_buttons[9].click()
    assert cards.currentRow()==9 and PRODUCTS[9]['short_name'] in p.product_text.text()
    p.set_data(deepcopy(p.data),p.actor);app.processEvents()
    assert cards.currentRow()==9 and cards.page==1
    cards.previous.click();app.processEvents()
    assert cards.page==0 and cards.currentRow()==9  # Browsing does not change purchase selection.
    cards.select_buttons[0].click();assert cards.currentRow()==0


def test_two_step_form_requires_answers_and_emits_only_confirmation_request(page):
    from PySide6.QtWidgets import QLineEdit
    p,app=page;d=p.questionnaire;p.open_profile();calls=[];p.requested.connect(lambda *args:calls.append(args))
    d.next.click();assert d.pages.currentIndex()==0 and d.error.text()
    for key,value in FIELDS.items():
        w=p.fields[key]
        if isinstance(w,QLineEdit):w.setText(value)
        else:w.setCurrentIndex(w.findData(value))
    p.fields['budget'].setText('1e3');d.next.click();assert d.pages.currentIndex()==0
    p.fields['budget'].setText(FIELDS['budget']);d.next.click();assert d.pages.currentIndex()==1
    assert d.save.isVisible();d.save.click()
    assert calls==[('SAVE_WEALTH_PROFILE',FIELDS)] and not d.isVisible()
    assert not p.data['profile_valid']  # Server confirmation, not a click, changes saved state.
    p.set_available(False);p.maybe_onboard();assert not d.isVisible()


def test_valid_profile_reused_expired_profile_prompts_again(page):
    p,app=page;p.questionnaire.reject()
    data=deepcopy(p.data)
    data.update(profile_valid=True,profile=dict(recorded_at='2026-11-01T12:00:00+08:00',expires_on='2027-11-01',answers=ANSWERS))
    p.set_data(data,p.actor);p.maybe_onboard();assert not p.questionnaire.isVisible()
    p.hide();p.show();app.processEvents();assert not p.questionnaire.isVisible()
    p.edit_profile.click();assert p.questionnaire.isVisible() and p.fields['budget'].text()=='20000.00'
    p.questionnaire.reject();data['profile_valid']=False;data['profile']['expires_on']='2026-10-31'
    before=len(p.interview_events)
    p.set_data(data,p.actor);p.maybe_onboard();assert not p.questionnaire.isVisible() and len(p.interview_events)==before+1


def test_account_switch_closes_dialog_and_clears_draft(page):
    p,app=page;p.fields['budget'].setText('1234');data=deepcopy(p.data)
    p.set_data(data,('bob','account-b'))
    assert not p.questionnaire.isVisible() and p.fields['budget'].text()==''
    p.maybe_onboard();assert not p.questionnaire.isVisible() and len(p.interview_events)==2
