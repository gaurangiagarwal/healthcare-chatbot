(() => {
  const locate = document.getElementById('locate');
  const locationInput = document.getElementById('location');
  const locationStatus = document.getElementById('location-status');
  const osmForm = document.getElementById('osm-search-form');
  const osmButton = document.getElementById('osm-search-button');
  const osmResults = document.getElementById('osm-results');
  const osmAttribution = document.getElementById('osm-attribution');
  const directoryForm = document.querySelector('form.finder-form[method="get"]');
  if (locate) locate.addEventListener('click', () => {
    const reportLocation = (message) => {
      if (!locationStatus) return;
      locationStatus.textContent = message;
      locationStatus.hidden = false;
    };
    if (!navigator.geolocation) { reportLocation('Location is unavailable. Enter a city or coordinates instead.'); return; }
    locate.disabled = true;
    locate.textContent = 'Getting location...';
    navigator.geolocation.getCurrentPosition((position) => {
      locationInput.value = `${position.coords.latitude},${position.coords.longitude}`;
      locate.disabled = false;
      locate.textContent = 'Use my location';
      if (osmForm) osmForm.requestSubmit();
      else if (directoryForm) directoryForm.requestSubmit();
      else reportLocation('Nearby mapped search is unavailable. The directory list remains available.');
    }, () => {
      locate.disabled = false;
      locate.textContent = 'Use my location';
      reportLocation('Location was not shared. Enter a city or coordinates instead.');
    }, {enableHighAccuracy: false, timeout: 8000});
  });

  const mapNode = document.getElementById('map');
  const dataNode = document.getElementById('hospital-data');
  const mapMessage = document.getElementById('map-message');
  const libraryStatus = document.getElementById('map-library-status');
  const tileStatus = document.getElementById('map-tile-status');
  const providerStatus = document.getElementById('map-provider-status');
  if (!mapNode) return;
  if (providerStatus) providerStatus.textContent = 'Tile provider: OpenStreetMap standard raster tiles.';
  const showMapMessage = (message) => {
    if (!mapMessage) return;
    mapMessage.textContent = `${message} Use the facility list to browse results.`;
    mapMessage.hidden = false;
  };
  let hospitals = [];
  let map;
  const markers = new Map();
  if (!dataNode) showMapMessage('Map data is unavailable.');
  else if (!window.L) {
    if (libraryStatus) libraryStatus.textContent = 'Map library: failed to load.';
    if (tileStatus) tileStatus.textContent = 'Tile requests: not started.';
    showMapMessage('The map library did not load.');
  }
  else {
    try {
      if (libraryStatus) libraryStatus.textContent = 'Map library: Leaflet loaded.';
      hospitals = JSON.parse(dataNode.textContent);
      map = window.L.map(mapNode).setView([20.59, 78.96], 4);
      if (tileStatus) tileStatus.textContent = 'Tile requests: loading; referrer policy enabled.';
      const tiles = window.L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        referrerPolicy: 'strict-origin-when-cross-origin',
      }).addTo(map);
      let mapHasError = false;
      tiles.on('tileerror', () => {
        mapHasError = true;
        if (tileStatus) tileStatus.textContent = 'Tile requests: failed; inspect browser network details for the HTTP cause. No automatic retry was made.';
        showMapMessage('Map tiles were blocked or could not be loaded.');
      });
      tiles.on('load', () => {
        if (mapHasError) return;
        if (tileStatus) tileStatus.textContent = 'Tile requests: loaded successfully.';
        if (markers.size && mapMessage) mapMessage.hidden = true;
        else showMapMessage('The map loaded, but no facility has valid coordinates.');
      });
      hospitals.forEach((hospital) => {
        const latitude = Number(hospital.latitude);
        const longitude = Number(hospital.longitude);
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)
          || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) return;
        const marker = window.L.marker([latitude, longitude]).addTo(map);
        const popup = document.createElement('div');
        const title = document.createElement('strong'); title.textContent = hospital.name || 'Name not available in map data';
        const status = document.createElement('div'); status.textContent = `${hospital.source || 'MediReach'} | ${hospital.trust_label || hospital.verification_status || 'Status unknown'}`;
        popup.append(title, status);
        marker.bindPopup(popup);
        markers.set(String(hospital.result_id || `managed:hospital:${hospital.id}`), marker);
      });
      if (markers.size) map.fitBounds(window.L.featureGroup([...markers.values()]).getBounds().pad(.15));
      else showMapMessage('No facilities have valid map coordinates.');
    } catch (error) {
      if (libraryStatus && !window.L) libraryStatus.textContent = 'Map library: failed to load.';
      if (tileStatus) tileStatus.textContent = 'Tile requests: map initialization failed before tiles loaded.';
      showMapMessage('The map could not be initialized.');
      console.error('MediReach map initialization failed:', error);
      map = null;
    }
  }

  const osmMarkers = map ? window.L.layerGroup().addTo(map) : null;
  if (osmForm && osmButton && osmResults) {
    osmForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      osmButton.disabled = true;
      osmForm.setAttribute('aria-busy', 'true');
      osmButton.textContent = 'Searching OpenStreetMap...';
      osmResults.hidden = false;
      osmResults.replaceChildren();
      const loading = document.createElement('p');
      loading.textContent = 'Loading nearby mapped facilities...';
      osmResults.append(loading);
      try {
        const coordinates = await requestedCoordinates(locationInput?.value || '');
        const field = (name) => directoryForm?.querySelector(`[name="${name}"]`);
        const checked = (name) => Boolean(directoryForm?.querySelector(`[name="${name}"]:checked`));
        const response = await fetch(osmForm.dataset.endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': osmForm.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
          },
          body: JSON.stringify({
            result_types: ['hospital'],
            include_osm: true,
            query: field('q')?.value || '',
            location: field('location')?.value || '',
            facility_type: field('facility_type')?.value || '',
            specialty: field('specialty')?.value || '',
            trust_category: osmForm.querySelector('[name="nearby_trust_category"]')?.value || field('trust_category')?.value || '',
            source_category: field('source_category')?.value || '',
            emergency: checked('emergency'),
            icu: checked('icu'),
            trauma: checked('trauma'),
            latitude: coordinates.latitude,
            longitude: coordinates.longitude,
            radius_km: Number(osmForm.querySelector('[name="radius_km"]').value),
          }),
        });
        let data;
        try {
          data = await response.json();
        } catch (_) {
          throw new Error('The nearby search returned an unreadable response. Please try again.');
        }
        if (!response.ok) {
          throw new Error(response.status >= 500
            ? 'The nearby search is temporarily unavailable. Your directory list is still available.'
            : 'Check the coordinates and search settings, then try again.');
        }
        if (!Array.isArray(data?.results)) {
          throw new Error('The nearby search returned an incomplete result. Your directory list is still available.');
        }
        const providerSearchStatus = document.getElementById('provider-search-status');
        if (providerSearchStatus) providerSearchStatus.textContent = `Provider search: ${data.results.length} result(s); ${data.source_errors?.length || 0} source error(s).`;
        loading.remove();
        osmMarkers?.clearLayers();
        const heading = document.createElement('h2');
        heading.className = 'h5';
        heading.textContent = `Nearby discovery results (${data.results.length})`;
        osmResults.append(heading);
        const disclaimer = document.createElement('p');
        disclaimer.textContent = 'MediReach-managed directory records and OpenStreetMap mapped listings are separate sources. OpenStreetMap listings are not independently verified and do not confirm that a facility is open or accepting patients.';
        osmResults.append(disclaimer);
        (data.results || []).forEach((facility) => renderOsmFacility(facility, osmResults, osmMarkers));
        (data.source_errors || []).forEach((sourceError) => {
          const errorMessage = document.createElement('p');
          errorMessage.className = 'text-danger';
          errorMessage.setAttribute('role', 'status');
          errorMessage.textContent = `${sourceError.source || 'A discovery source'} is temporarily unavailable.`;
          osmResults.append(errorMessage);
        });
        if (map && data.results?.length) {
          const mappedBounds = data.results.map((facility) => [facility.latitude ?? facility.coordinates?.latitude, facility.longitude ?? facility.coordinates?.longitude])
            .filter((point) => Number.isFinite(Number(point[0])) && Number.isFinite(Number(point[1])));
          if (mappedBounds.length) map.fitBounds(window.L.latLngBounds(mappedBounds).pad(.15));
        }
        if (!data.results?.length && !data.source_errors?.length) {
          const empty = document.createElement('p');
          empty.textContent = 'No mapped healthcare facilities were found within this radius.';
          osmResults.append(empty);
        }
        if (osmAttribution && data.results.some((facility) => facility.source === 'OpenStreetMap')) osmAttribution.hidden = false;
      } catch (error) {
        loading.textContent = error instanceof TypeError
          ? 'Network error. Check your connection and try the nearby search again.'
          : (error.message || 'Mapped facility search failed. The directory list is still available.');
      } finally {
        osmForm.removeAttribute('aria-busy');
        osmButton.disabled = false;
        osmButton.textContent = 'Find mapped facilities nearby';
      }
    });
  }

  async function requestedCoordinates(value) {
    const match = value.trim().match(/^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/);
    if (match) return {latitude: Number(match[1]), longitude: Number(match[2])};
    if (value.trim()) return {location: value.trim()};
    if (!navigator.geolocation) throw new Error('Enter latitude, longitude or enable browser location for this search.');
    return new Promise((resolve, reject) => navigator.geolocation.getCurrentPosition(
      (position) => resolve({latitude: position.coords.latitude, longitude: position.coords.longitude}),
      () => reject(new Error('Location was not shared. Enter latitude, longitude or allow browser location.')),
      {enableHighAccuracy: false, timeout: 8000},
    ));
  }

  function renderOsmFacility(facility, container, markerLayer) {
    const card = document.createElement('article');
    card.className = 'hospital-card';
    const title = document.createElement('h3');
    title.className = 'h6';
    title.textContent = facility.name || (facility.source === 'OpenStreetMap' ? 'Name not available in OpenStreetMap tags' : 'Name not available');
    card.append(title);
    const sourceLabel = document.createElement('p');
    sourceLabel.textContent = `Source: ${facility.source || 'OpenStreetMap'}`;
    card.append(sourceLabel);
    const categoryValue = facility.facility_category || facility.facility_type;
    if (categoryValue) {
      const category = document.createElement('p');
      category.textContent = `${facility.source === 'MediReach' ? 'Facility type' : 'Mapped category'}: ${categoryValue}`;
      card.append(category);
    }
    if (facility.location && Object.keys(facility.location).length) {
      const address = document.createElement('p');
      address.textContent = Object.values(facility.location).join(', ');
      card.append(address);
    } else if (facility.address && typeof facility.address === 'string') {
      const address = document.createElement('p'); address.textContent = facility.address; card.append(address);
    }
    (facility.specialties || []).forEach((value) => { const item = document.createElement('p'); item.textContent = `Specialty: ${value}`; card.append(item); });
    (facility.services || []).forEach((value) => { const item = document.createElement('p'); item.textContent = `Reported service: ${value.name} (${value.status_label || value.status})`; card.append(item); });
    (facility.contact_information || []).forEach((value) => { const item = document.createElement('p'); item.textContent = `${value.type}: ${value.value} (${value.label})`; card.append(item); });
    const trust = document.createElement('p');
    trust.className = facility.source === 'OpenStreetMap' ? 'status-chip trust-status mapped' : `status-chip trust-status ${facility.provider_status || 'unknown'}`;
    trust.textContent = facility.trust_label;
    card.append(trust);
    const sourceLink = document.createElement('a');
    if (facility.source === 'OpenStreetMap' && facility.source_url?.startsWith('https://')) {
      sourceLink.href = facility.source_url;
      sourceLink.textContent = 'View OpenStreetMap record';
      sourceLink.target = '_blank';
      sourceLink.rel = 'noopener noreferrer';
      card.append(sourceLink);
    } else if (facility.result_type === 'hospital' && facility.id) {
      sourceLink.href = `/hospitals/${facility.id}/`;
      sourceLink.textContent = 'View MediReach facility record';
      card.append(sourceLink);
    }
    container.append(card);

    const latitude = facility.latitude ?? facility.coordinates?.latitude;
    const longitude = facility.longitude ?? facility.coordinates?.longitude;
    if (markerLayer && Number.isFinite(Number(latitude)) && Number.isFinite(Number(longitude))) {
      const marker = window.L.marker([Number(latitude), Number(longitude)]).addTo(markerLayer);
      const popup = document.createElement('div');
      const popupName = document.createElement('strong');
      popupName.textContent = title.textContent;
      const popupTrust = document.createElement('div');
      popupTrust.textContent = `${facility.source || 'OpenStreetMap'} · ${facility.trust_label}`;
      popup.append(popupName, popupTrust);
      marker.bindPopup(popup);
    }
  }

  document.querySelectorAll('.hospital-card[data-map-id]').forEach((card) => card.addEventListener('mouseenter', () => {
    const marker = markers.get(card.dataset.mapId);
    if (marker) marker.openPopup();
  }));
})();
