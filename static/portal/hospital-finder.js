(() => {
  const locate = document.getElementById('locate');
  const locationInput = document.getElementById('location');
  if (locate) locate.addEventListener('click', () => {
    if (!navigator.geolocation) { window.alert('Location is unavailable. Enter a city or coordinates instead.'); return; }
    locate.disabled = true;
    locate.textContent = 'Getting location...';
    navigator.geolocation.getCurrentPosition((position) => {
      locationInput.value = `${position.coords.latitude},${position.coords.longitude}`;
      locate.form.requestSubmit();
    }, () => {
      locate.disabled = false;
      locate.textContent = 'Use my location';
      window.alert('Location permission was not available. Enter a city or coordinates instead.');
    }, {enableHighAccuracy: false, timeout: 8000});
  });

  const mapNode = document.getElementById('map');
  const dataNode = document.getElementById('hospital-data');
  if (!mapNode || !dataNode || !window.L) return;
  const hospitals = JSON.parse(dataNode.textContent);
  const map = window.L.map(mapNode).setView([20.59, 78.96], 4);
  window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution: '&copy; OpenStreetMap contributors'}).addTo(map);
  const markers = new Map();
  hospitals.forEach((hospital) => {
    if (hospital.latitude == null || hospital.longitude == null) return;
    const marker = window.L.marker([Number(hospital.latitude), Number(hospital.longitude)]).addTo(map);
    const popup = document.createElement('div');
    const title = document.createElement('strong'); title.textContent = hospital.name;
    const city = document.createElement('div'); city.textContent = `${hospital.city} | ${hospital.verification_status}`;
    popup.append(title, city);
    marker.bindPopup(popup);
    markers.set(String(hospital.id), marker);
  });
  if (markers.size) map.fitBounds(window.L.featureGroup([...markers.values()]).getBounds().pad(.15));
  document.querySelectorAll('.hospital-card').forEach((card, index) => card.addEventListener('mouseenter', () => {
    const hospital = hospitals[index];
    const marker = hospital && markers.get(String(hospital.id));
    if (marker) marker.openPopup();
  }));
})();
