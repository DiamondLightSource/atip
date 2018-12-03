import atip
import at
import pytest


@pytest.fixture()
def at_elem():
    e = at.elements.Drift('D1', 0.0, KickAngle=[0, 0], Index=1, Frequency=0,
                          k=0.0, PolynomA=[0, 0, 0, 0], PolynomB=[0, 0, 0, 0])
    return e


@pytest.fixture()
def at_elem_preset():
    e = at.elements.Drift('D1', 0.5, KickAngle=[0.1, 0.01], Index=6, k=-0.07,
                          Frequency=500, PolynomA=[1.3, 13, 22, 90],
                          PolynomB=[8, -0.07, 42, 1])
    return e
