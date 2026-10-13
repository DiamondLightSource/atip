# ATIP example

## Simmulating accelerator physics using ATIP as a data source for Pytac

Note that you need an AT lattice that is compatible with Pytac. Some are provided
in ``atip/rings/``, otherwise try running the Matlab function
``atip/rings/create_lattice_matfile.m`` with an AT lattice loaded.

:::{code-block} python

>>> import pytac
>>> import atip
>>> # Load the DIAD lattice from Pytac.
>>> lat = pytac.load_csv.load('DIAD')
>>> # Load the AT sim into the Pytac lattice.
>>> atip.load_sim.load_from_filepath(lat, 'atip/rings/DIAD.mat')
>>> # Use the sim by default.
>>> lat.set_default_data_source(pytac.SIM)
>>> # The initial beam position is zero.
>>> lat.get_value('x')
array([0., 0., 0., ..., 0., 0., 0.])
>>> # Get the first horizontal corrector magnet and set its current to 1A.
>>> hcor1 = lat.get_elements('HSTR')[0]
>>> hcor1.set_value('x_kick', 1, units=pytac.ENG)
>>> # Now the x beam position has changed.
>>> lat.get_value('x')
array([0.00240101, 0.00240101, 0.00239875, ..., 0.00240393, 0.00240327,
        0.00240327])
:::
