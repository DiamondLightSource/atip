function create_lattice_matfile(filename)
% Creates a .mat file AT lattice compatible with ATIP.
% If a filename is given that file will be updated to ATIP standard. Otherwise
% ATIP_RING is initially taken from 'THERING' global variable and save as
% 'lattice.mat'.
    if ~(nargin == 0)
        load(filename, 'ATIP_RING');
    end
    if ~exist('ATIP_RING', 'var')
        global THERING;
        ATIP_RING = THERING;
        if isempty(ATIP_RING)
                disp('THERING global variable is empty, try running storageringinit(Ringmode). Exiting with error.');
                exit(1)
        else
            disp('Using global THERING and saving it to global ATIP_RING.');
        end
    else
        disp('Using loaded ATIP_RING from file.');
    end
    fprintf('Initial lattice has dimensions: %s\n', mat2str(size(ATIP_RING)))
    % Correct dimension order if necessary.
    if size(ATIP_RING, 1) == 1
        ATIP_RING = permute(ATIP_RING, [2 1]);
    end
    % Correct classes and pass methods.
    for x = 1:length(ATIP_RING)
        if strcmp(ATIP_RING{x, 1}.FamName, 'BPM10')
            % Wouldn't be correctly classed by class guessing otherwise.
            ATIP_RING{x, 1}.Class = 'Monitor';
        elseif (strcmp(ATIP_RING{x, 1}.FamName, 'HSTR') || strcmp(ATIP_RING{x, 1}.FamName, 'VSTR'))
            ATIP_RING{x, 1}.Class = 'Corrector';
        elseif (strcmp(ATIP_RING{x, 1}.FamName, 'HTRIM') || strcmp(ATIP_RING{x, 1}.FamName, 'VTRIM'))
            ATIP_RING{x, 1}.Class = 'Corrector';
        end

        if isfield(ATIP_RING{x, 1}, 'Class')
            if strcmp(ATIP_RING{x, 1}.Class, 'SEXT')
                ATIP_RING{x, 1}.Class = 'Sextupole';
            end
        end

        if strcmp(ATIP_RING{x, 1}.PassMethod, 'GWigSymplecticPass')
            ATIP_RING{x, 1}.Class = 'Wiggler';
        end
    end

    % Remove elements. Done this way because the size of ATIP_RING changes
    % during the loop.
    y = 1;  
    while y < length(ATIP_RING)
        % The data within the deleted elements is not needed
        if strcmp(ATIP_RING{y, 1}.FamName, 'HSTR') && ATIP_RING{y, 1}.Length == 0 && (strcmp(ATIP_RING{y-1, 1}.Class, 'Sextupole') || strcmp(ATIP_RING{y-1, 1}.Class, 'Multipole'))
            ATIP_RING(y, :) = [];  % Delete hstrs that are preceded by a sextupole or multipole.
        elseif strcmp(ATIP_RING{y, 1}.FamName, 'VSTR') && ATIP_RING{y, 1}.Length == 0 && (strcmp(ATIP_RING{y-1, 1}.Class, 'Sextupole') || strcmp(ATIP_RING{y-1, 1}.Class, 'Multipole'))
            ATIP_RING(y, :) = [];  % Delete vstrs that are preceded by a sextupole or multipole.
        else
            y = y + 1;
        end
    end

    if isfield(ATIP_RING{1, 1}, 'TwissData')
        ATIP_RING{1, 1} = rmfield(ATIP_RING{1, 1}, 'TwissData');
    end

    fprintf('Converted ATIP_RING has dimensions: %s\n', mat2str(size(ATIP_RING)))
    if nargin == 0
        save('lattice.mat', 'ATIP_RING');
    else
        save(filename, 'ATIP_RING');
    end
end
