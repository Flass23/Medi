const map = L.map('map').setView([40.7128, -74.0060], 14);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let deliveryMarker = null;
let customerMarkers = {};
let activeOrderId = null;

function updateMap() {
  fetch('/api/orders')
    .then(res => res.json())
    .then(data => {
      const { orders, delivery, target } = data;
      activeOrderId = target;

      // Update delivery location
      if (!deliveryMarker) {
        deliveryMarker = L.marker([delivery.lat, delivery.lng], {
          icon: L.icon({
            iconUrl: 'https://cdn-icons-png.flaticon.com/512/684/684908.png',
            iconSize: [30, 30]
          })
        }).addTo(map).bindPopup("You (Delivery Guy)");
      } else {
        deliveryMarker.setLatLng([delivery.lat, delivery.lng]);
      }

      // Add/update customer markers
      orders.forEach(order => {
        const isActive = order.id === target;
        const iconColor = isActive ? 'red' : 'blue';

        const icon = L.icon({
          iconUrl: `https://maps.google.com/mapfiles/ms/icons/${iconColor}-dot.png`,
          iconSize: [32, 32],
          iconAnchor: [16, 32],
          popupAnchor: [0, -32]
        });

        if (!customerMarkers[order.id]) {
          const marker = L.marker([order.lat, order.lng], { icon });
          marker.bindPopup(`
            <strong>${order.name}</strong><br>
            <button onclick="setActiveOrder(${order.id})">Deliver this order</button>
          `);
          marker.addTo(map);
          customerMarkers[order.id] = marker;
        } else {
          customerMarkers[order.id].setLatLng([order.lat, order.lng]);
          customerMarkers[order.id].setIcon(icon);
        }
      });
    });
}

function setActiveOrder(orderId) {
  fetch(`/api/set_target/${orderId}`, { method: 'POST' })
    .then(() => updateMap());
}

// Simulate delivery guy movement with actual browser geolocation
function updateDeliveryLocation() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      fetch('/api/update_delivery', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude
        })
      });
    });
  }
}

// Repeat every 4 seconds
setInterval(() => {
  updateMap();
  updateDeliveryLocation();
}, 4000);

// Initial load
updateMap();
updateDeliveryLocation();
