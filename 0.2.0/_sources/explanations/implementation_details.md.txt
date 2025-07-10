# Implementation details

All the accelerator data for the simulator is held in an ATSimulator object, which is referenced by the data sources of the lattice and each element.Each Pytac element has an equivalent pyAT element, held in a ATElementDataSource; when a get request is made, the appropriate data from that AT element is returned.

The ATSimulator object has a queue of pending changes. When a set request is received by an element, the element puts the changes onto the queue of the ATSimulator. Inside the ATSimulator a Cothread thread checks the length of the queue. When it sees changes on the queue, the thread recalculates the physics data of the lattice to ensure that it is up to date. This means that the emittance and linear optics data held by ATSimulator is updated after every batch of changes, and that without excessive calculation a very recent version of the lattice's physics data is always available.

## API:

load_sim:

        load_from_filepath(pytac_lattice, at_lattice_filepath, callback=None) - loads the AT lattice from the given filepath to the .mat file and then calls load.
        load(pytac_lattice, at_lattice, callback=None) - loads the simulator onto the passed Pytac lattice, callback is a callable that is passed to ATSimulator during creation to be called on completion of each round of physics calculations.

ATElementDataSource:

        get_fields() - return the fields on the element.
        add_field(field) - add the given field to this element's data source.
        get_value(field) - get the value for a given field on the element.
        set_value(field, value) - set the value for a given field on the element, appends the change to the queue.

ATLatticeDataSource:

        get_fields() - return the fields on the lattice.
        get_value(field) - get the value for a given field on the lattice.
        set_value(field, set_value) - set the value for a given field on the lattice, currently not supported so raises HandleException.

ATSimulator:

        toggle_calculations() - pause or unpause the recalculation thread.
        wait_for_calculations(timeout=10) - wait up to 'timeout' seconds for the current calculations to conclude, if they do it returns True, if not False is returned; if 'timeout' is not passed it will wait 10 seconds.
        get_at_element(index) - return a shallow copy of the specified AT element from the central AT ring, N.B. An 'index' of 1 returns ring[0].
        get_at_lattice() - return a shallow copy of the entire centralised AT lattice object.
        get_s() - return the 's position' of every element in the lattice.
        get_total_bend_angle() - return the total bending angle of all the dipoles in the lattice.
        get_total_absolute_bend_angle() - return the total absolute bending angle of all the dipoles in the lattice.
        get_energy() - return the energy of the lattice.
        get_tune(field) - return the specified plane of the lattice's 'tune'; 'x' or 'y'.
        get_chromaticity(field) - return the specified plane of the lattice's 'chromaticity'; 'x' or 'y'.
        get_orbit(field) - return the specified plane of the lattice's 'closed orbit'; 'x', 'phase_x', 'y', or 'phase_y'.
        get_dispersion() - return the 'dispersion' vector for every element in the lattice.
        get_alpha() - return the 'alpha' vector at every element in the lattice.
        get_beta() - return the 'beta' vector at every element in the lattice.
        get_mu() - return 'mu' at every element in the lattice.
        get_m44() - return the 4x4 transfer matrix for every element in the lattice.
        get_emittance(field) - return the specified plane of the lattice's 'emittance'; 'x' or 'y'.
        get_radiation_integrals() - return the 5 Synchrotron Integrals for the lattice.
        get_momentum_compaction() - return the momentum compaction factor for the lattice.
        get_energy_spread() - return the energy spread for the lattice.
        get_energy_loss() - return the energy loss per turn of the lattice.
        get_damping_partition_numbers() - return the damping partition numbers for the lattice's three normal modes.
        get_damping_times() - return the damping times for the lattice's three normal modes.
        get_linear_dispersion_action() - return the Linear Dispersion Action ("curly H") for the lattice.
        get_horizontal_emittance() - return the horizontal ('x') emittance for the lattice calculated from the radiation integrals.
