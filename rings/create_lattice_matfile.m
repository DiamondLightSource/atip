function create_lattice_matfile(filename)
% Creates a .mat file AT lattice compatible with ATIP.
% If a filename is given that file will be updated to ATIP standard. Otherwise
% the ring is taken from either of the 'RING' or 'THERING' global variables,
% with 'RING' taking priority. If a filename is not passed the updated lattice
% will be stored in 'lattice.mat'.
    if ~(nargin == 0)
        load(filename, 'RING');
    end
    if ~exist('RING', 'var')
        global RING;
        if isempty(RING)
            global THERING;
            RING = THERING;
        end
    end
    if isempty(RING)
        disp('Unable to load a ring from file or global variables.');
        return;
    end
    % Correct dimension order if necessary.
    if size(RING, 1) == 1
        RING = permute(RING, [2 1]);
    end
    % Correct classes and pass methods.
    for x = 1:length(RING)
        if strcmp(RING{x, 1}.FamName, 'BPM10')
            % Wouldn't be correctly classed by class guessing otherwise.
            RING{x, 1}.Class = 'Monitor';
        elseif (strcmp(RING{x, 1}.FamName, 'HSTR') || strcmp(RING{x, 1}.FamName, 'VSTR'))
            RING{x, 1}.Class = 'Corrector';
        elseif (strcmp(RING{x, 1}.FamName, 'HTRIM') || strcmp(RING{x, 1}.FamName, 'VTRIM'))
            RING{x, 1}.Class = 'Corrector';
        end
        if isfield(RING{x, 1}, 'Class')
            if strcmp(RING{x, 1}.Class, 'SEXT')
                RING{x, 1}.Class = 'Sextupole';
            end
        end
        if strcmp(RING{x, 1}.PassMethod, 'ThinCorrectorPass')
            % ThinCorrectorPass no longer exists in AT.
            RING{x, 1}.PassMethod = 'CorrectorPass';
        elseif strcmp(RING{x, 1}.PassMethod, 'GWigSymplecticPass')
            RING{x, 1}.Class = 'Wiggler';
        end
    end

    % Remove elements. Done this way because the size of RING changes during
    % the loop.
    y = 1;  
    while y < length(RING)
        % I should probably transfer the attributes of the deleted corrector
        % elements to the sextupole but cba.
        if (strcmp(RING{y, 1}.FamName, 'HSTR') && strcmp(RING{y-1, 1}.Class, 'Sextupole'))
            RING(y, :) = [];  % Delete hstrs that are preceded by a sextupole.
        elseif (strcmp(RING{y, 1}.FamName, 'VSTR') && strcmp(RING{y-1, 1}.Class, 'Sextupole'))
            RING(y, :) = [];  % Delete vstrs that are preceded by a sextupole.
        else
            y = y + 1;
        end
    end
    if isfield(RING{1, 1}, 'TwissData')
        RING{1, 1} = rmfield(RING{1, 1}, 'TwissData');
    end
    if nargin == 0
        save('lattice.mat', 'RING');
    else
        save(filename, 'RING');
    end
end
