from bot.matching import rank_trips


def trip(id, districts, slot="morning", seats=4, lat=None, lon=None, direction="F2T", driver=100):
    return dict(id=id, driver_id=driver + id, direction=direction, districts=",".join(districts),
                trip_date="2026-11-21", slot=slot, seats_free=seats, status="active", lat=lat, lon=lon)


def req(fergana="qoqon", tashkent="chilonzor", slot="morning", seats=1, lat=None, lon=None, direction="F2T"):
    return dict(id=1, passenger_id=1, direction=direction, fergana_code=fergana, tashkent_code=tashkent,
                trip_date="2026-11-21", slot=slot, seats=seats, lat=lat, lon=lon)


def test_district_must_be_covered():
    trips = [trip(1, ["quva", "margilon"]), trip(2, ["qoqon", "dangara", "beshariq"])]
    assert [m.trip_id for m in rank_trips(req(), trips)] == [2]


def test_nearest_driver_first():
    # Ikkala haydovchi ham Qo'qonni oladi, biri Qo'qonda, biri Farg'onada turibdi
    far = trip(1, ["qoqon"], lat=40.3864, lon=71.7864)
    near = trip(2, ["qoqon"], lat=40.53, lon=70.95)
    ranked = rank_trips(req(lat=40.5286, lon=70.9425), [far, near])
    assert [m.trip_id for m in ranked] == [2, 1]
    assert ranked[0].distance_km < 2


def test_base_district_used_without_location():
    a = trip(1, ["quva", "qoqon"])  # bazasi Quva
    b = trip(2, ["dangara", "qoqon"])  # bazasi Dang'ara — Qo'qonga yaqin
    assert rank_trips(req(), [a, b])[0].trip_id == 2


def test_seats_slot_direction_and_exclusion():
    trips = [
        trip(1, ["qoqon"], seats=1),
        trip(2, ["qoqon"], slot="evening"),  # 2 oraliq farq
        trip(3, ["qoqon"], direction="T2F"),
        trip(4, ["qoqon"], slot="day"),  # qo'shni oraliq — mos
        trip(5, ["qoqon"]),
    ]
    assert [m.trip_id for m in rank_trips(req(seats=2), trips)] == [5, 4]
    assert [m.trip_id for m in rank_trips(req(seats=2), trips, {5})] == [4]


def test_from_tashkent_uses_tashkent_pickup():
    t1 = trip(1, ["qoqon"], direction="T2F", lat=41.364, lon=69.285)  # Yunusobod
    t2 = trip(2, ["qoqon"], direction="T2F", lat=41.273, lon=69.204)  # Chilonzor
    r = req(direction="T2F", tashkent="chilonzor")
    assert [m.trip_id for m in rank_trips(r, [t1, t2])] == [2, 1]
