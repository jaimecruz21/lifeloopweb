const CodeAddress = function () {
    let geocoder, map;

    const init = function () {
        let address = $('[data-address]').data('address');

        geocoder = new google.maps.Geocoder();
        geocoder.geocode({
            'address': address
        }, function (results, status) {
            if (status === google.maps.GeocoderStatus.OK) {
                let myOptions = {
                    zoom: 15,
                    center: results[0].geometry.location,
                    mapTypeId: google.maps.MapTypeId.ROADMAP
                };

                map = new google.maps.Map(document.getElementById('map'), myOptions);

                let marker = new google.maps.Marker({
                    map: map,
                    position: results[0].geometry.location,
                    title: address
                });

                let infowindow = new google.maps.InfoWindow({
                    content: address
                });
                marker.addListener('click', function () {
                    infowindow.open(map, marker);
                });
                document.getElementById('map').style.height = '250px';
            } else {
                document.getElementById('map').style.display = 'none';
            }
        });
    };

    return {
        init: init
    }
}();

export {CodeAddress};
