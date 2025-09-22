function create_lattice_matfile(filename)
% Creates a .mat file AT lattice compatible with ATIP.
% If a filename is given that file will be updated to ATIP standard. Otherwise
% THERING is taken from either of the 'RING' or 'THERING' global variables,
% with 'THERING' taking priority. If a filename is not passed the updated lattice
% will be stored in 'lattice.mat'.
    if ~(nargin == 0)
        load(filename, 'THERING');
    end
    if ~exist('THERING', 'var')
        global THERING;
        if isempty(THERING)
            global RING;
            if isempty(RING)
                disp('Both RING and THERING are empty, try running storageringinit(Ringmode). Exiting with error.');
                exit(1)
            else
                THERING = RING;
                disp('THERING is empty, using RING.');
            end
        else
            disp('Using THERING.');
        end
    end
    fprintf('Initial THERING has dimensions: %s\n', mat2str(size(THERING)))
    % Correct dimension order if necessary.
    if size(THERING, 1) == 1
        THERING = permute(THERING, [2 1]);
    end
    % Correct classes and pass methods.
    for x = 1:length(THERING)
        if strcmp(THERING{x, 1}.FamName, 'BPM10')
            % Wouldn't be correctly classed by class guessing otherwise.
            THERING{x, 1}.Class = 'Monitor';
        elseif (strcmp(THERING{x, 1}.FamName, 'HSTR') || strcmp(THERING{x, 1}.FamName, 'VSTR'))
            THERING{x, 1}.Class = 'Corrector';
        elseif (strcmp(THERING{x, 1}.FamName, 'HTRIM') || strcmp(THERING{x, 1}.FamName, 'VTRIM'))
            THERING{x, 1}.Class = 'Corrector';
        end

        if isfield(THERING{x, 1}, 'Class')
            if strcmp(THERING{x, 1}.Class, 'SEXT')
                THERING{x, 1}.Class = 'Sextupole';
            end
        end

        if strcmp(THERING{x, 1}.PassMethod, 'GWigSymplecticPass')
            THERING{x, 1}.Class = 'Wiggler';
        end
    end

    % Remove elements. Done this way because the size of THERING changes
    % during the loop.
    y = 1;  
    while y < length(THERING)
        % The data within the deleted elements is not needed
        if strcmp(THERING{y, 1}.FamName, 'HSTR') && THERING{y, 1}.Length == 0 &&(strcmp(THERING{y-1, 1}.Class, 'Sextupole') || strcmp(THERING{y-1, 1}.Class, 'Multipole'))
            THERING(y, :) = [];  % Delete hstrs that are preceded by a sextupole or multipole.
        elseif strcmp(THERING{y, 1}.FamName, 'VSTR') && THERING{y, 1}.Length == 0 && (strcmp(THERING{y-1, 1}.Class, 'Sextupole') || strcmp(THERING{y-1, 1}.Class, 'Multipole'))
            THERING(y, :) = [];  % Delete vstrs that are preceded by a sextupole or multipole.
        else
            y = y + 1;
        end
    end

    if isfield(THERING{1, 1}, 'TwissData')
        THERING{1, 1} = rmfield(THERING{1, 1}, 'TwissData');
    end

    fprintf('Converted THERING has dimensions: %s\n', mat2str(size(THERING)))
    if nargin == 0
        save('lattice.mat', 'THERING');
    else
        save(filename, 'THERING');
    end
end
