/*
 * CrisisNet map prototype.
 *
 * All rendering goes through applyPayload(payload). Today it is called once
 * after fetching sample_payload.json. Later, a WebSocket message can call
 * the same function, so live updates need no changes to the drawing code.
 */

const STATION_RADIUS_M = 22000;

const FACTOR_LABELS = {
  material: 'Building material',
  road_access: 'Road access',
  density: 'Area density',
  time_of_day: 'Time of day',
  occupancy_type: 'Facility type',
  compounding_penalty: 'Combined structural risk'
};

const OCCUPANCY_LABELS = {
  chemical: 'Chemical facility',
  garment_factory: 'Garment factory',
  mall: 'Shopping mall',
  industrial: 'Industrial site',
  residential: 'Residential',
  other: 'Other'
};

const map = L.map('map', { zoomControl: true, maxBoundsViscosity: 0.8 }).setView([23.8, 90.4], 7);

/* Basemap source. Online only: OpenStreetMap's tile servers do not allow
   offline use, so an offline demo needs a self-hosted tile source here. */
const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

L.tileLayer(TILE_URL, {
  minZoom: 6,
  maxZoom: 15,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const floodLayer = L.layerGroup().addTo(map);
const fireLayer = L.layerGroup().addTo(map);
const shelterLayer = L.layerGroup().addTo(map);
const warehouseLayer = L.layerGroup().addTo(map);

const layersControl = L.control.layers(null, {
  'Flood risk': floodLayer,
  'Fire incidents': fireLayer,
  'Shelters': shelterLayer,
  'Warehouses': warehouseLayer
}, { collapsed: false }).addTo(map);

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
  ));
}

/* ---------- Flood layer ---------- */

/* Single-hue ramp: probability 0 -> pale, 1 -> deep red-brown. Matches map.css. */
function probabilityColor(p) {
  const clamped = Math.min(1, Math.max(0, p));
  const lightness = 88 - clamped * 58;
  return `hsl(8, 70%, ${lightness}%)`;
}

function floodStyle(zone) {
  if (zone.error || zone.flood_probability == null) {
    return { color: '#9aa3ad', weight: 2, dashArray: '2 4', fillColor: '#9aa3ad', fillOpacity: 0.3 };
  }
  const manual = zone.data_source === 'manual';
  return {
    color: '#1b2430',
    weight: manual ? 2.5 : 1.5,
    dashArray: manual ? null : '6 5',
    fillColor: probabilityColor(zone.flood_probability),
    fillOpacity: 0.6
  };
}

function floodPopup(zone) {
  const title = `<h3 class="popup-title">${escapeHtml(zone.name)}</h3>`;
  if (zone.error) {
    return `${title}<p class="popup-note">No prediction available: ${escapeHtml(zone.error)}</p>`;
  }
  const source = zone.data_source === 'manual'
    ? 'Conditions entered by an admin'
    : 'Seasonal baseline for this month';
  const warnings = (zone.warnings || []).map(w => `<p class="popup-note">${escapeHtml(w)}</p>`).join('');
  return `${title}
    <table class="popup-table">
      <tr><th>Risk</th><td>${escapeHtml(zone.risk_label)}</td></tr>
      <tr><th>Flood probability</th><td>${Math.round(zone.flood_probability * 100)}%</td></tr>
      <tr><th>Data source</th><td>${escapeHtml(source)}</td></tr>
    </table>${warnings}`;
}

function renderFloodZones(zones) {
  floodLayer.clearLayers();
  zones.forEach(zone => {
    L.circle([zone.lat, zone.lon], { radius: STATION_RADIUS_M, ...floodStyle(zone) })
      .bindPopup(floodPopup(zone))
      .bindTooltip(zone.name, { direction: 'top' })
      .addTo(floodLayer);
  });
}

/* ---------- Fire layer ---------- */

function fireLevel(label) {
  if (label === 'High Escalation Risk') return 'high';
  if (label === 'Medium Escalation Risk') return 'medium';
  return 'standard';
}

function fireIcon(incident) {
  const level = fireLevel(incident.label);
  return L.divIcon({
    className: 'fire-icon',
    html: `<span class="fire-marker fire-${level}">` +
          '<span class="fire-ring"></span><span class="fire-core"></span></span>',
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -14]
  });
}

function firePopup(incident) {
  const occupancy = OCCUPANCY_LABELS[incident.occupancy_type] || incident.occupancy_type;
  const factorRows = Object.entries(incident.factors || {})
    .filter(([, points]) => points > 0)
    .map(([key, points]) =>
      `<tr><th>${escapeHtml(FACTOR_LABELS[key] || key)}</th><td>+${points}</td></tr>`)
    .join('');
  const floorNote = incident.floor_applied
    ? '<p class="popup-note">Rated high because of the facility type, whatever the other conditions.</p>'
    : '';
  return `<h3 class="popup-title">${escapeHtml(incident.name)}</h3>
    <table class="popup-table">
      <tr><th>Assessment</th><td>${escapeHtml(incident.label)}</td></tr>
      <tr><th>Risk score</th><td>${incident.score}</td></tr>
      <tr><th>Facility</th><td>${escapeHtml(occupancy)}</td></tr>
    </table>
    <p class="popup-note">What contributed to the score</p>
    <table class="popup-table">${factorRows}</table>${floorNote}`;
}

function renderFireIncidents(incidents) {
  fireLayer.clearLayers();
  incidents.forEach(incident => {
    const level = fireLevel(incident.label);
    L.marker([incident.lat, incident.lon], {
      icon: fireIcon(incident),
      zIndexOffset: level === 'high' ? 1000 : level === 'medium' ? 500 : 0,
      title: incident.name
    })
      .bindPopup(firePopup(incident))
      .bindTooltip(`${incident.name}: ${incident.label}`, { direction: 'top', offset: [0, -14] })
      .addTo(fireLayer);
  });
}

/* ---------- Shelters and warehouses ---------- */

function siteIcon(kind) {
  return L.divIcon({
    className: 'site-icon',
    html: `<span class="site site-${kind}"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    popupAnchor: [0, -8]
  });
}

function sitePopup(site, kindLabel) {
  const floodRows = site.risk_label
    ? `<tr><th>Nearest station</th><td>${escapeHtml(site.nearest_station)}</td></tr>
       <tr><th>Area flood risk</th><td>${escapeHtml(site.risk_label)}` +
       (site.flood_probability != null ? ` (${Math.round(site.flood_probability * 100)}%)` : '') +
       '</td></tr>'
    : '<tr><th>Area flood risk</th><td>No data</td></tr>';
  return `<h3 class="popup-title">${escapeHtml(site.name)}</h3>
    <table class="popup-table">
      <tr><th>Type</th><td>${kindLabel}</td></tr>${floodRows}
    </table>`;
}

function renderSites(layer, sites, kind, kindLabel) {
  layer.clearLayers();
  sites.forEach(site => {
    L.marker([site.lat, site.lon], { icon: siteIcon(kind), title: site.name })
      .bindPopup(sitePopup(site, kindLabel))
      .bindTooltip(site.name, { direction: 'top', offset: [0, -8] })
      .addTo(layer);
  });
}
/* ---------- Summary and entry point ---------- */

function renderSummary(payload) {
  const zones = payload.flood_risk_zones || [];
  const usable = zones.filter(z => !z.error);
  const fires = payload.fire_incidents || [];
  const set = (id, value) => { document.getElementById(id).textContent = value; };

  set('stat-total', zones.length);
  set('stat-high', usable.filter(z => z.risk_label === 'High').length);
  set('stat-low', usable.filter(z => z.risk_label === 'Low').length);
  set('stat-manual', zones.filter(z => z.data_source === 'manual').length);
  set('stat-error', zones.filter(z => z.error).length);
  set('stat-fire', fires.length);
  set('stat-fire-high', fires.filter(f => f.label === 'High Escalation Risk').length);

  const stamp = payload.generated_at ? new Date(payload.generated_at).toLocaleString() : 'unknown time';
  document.getElementById('timestamp').textContent = `Data as of ${stamp}`;
}

function applyPayload(payload) {
  renderFloodZones(payload.flood_risk_zones || []);
  renderFireIncidents(payload.fire_incidents || []);
  renderSites(shelterLayer, payload.shelters || [], 'shelter', 'Shelter');
  renderSites(warehouseLayer, payload.warehouses || [], 'warehouse', 'Warehouse');
  renderSummary(payload);
}

function showLoadError(message) {
  const box = document.createElement('div');
  box.className = 'load-error';
  box.setAttribute('role', 'alert');
  box.textContent = message;
  document.body.appendChild(box);
}

fetch('sample_payload.json')
  .then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(applyPayload)
  .catch(err => showLoadError(
    `Could not load sample_payload.json (${err.message}). ` +
    'Generate it first and serve this folder with a local web server.'
  ));