def test_health_returns_healthy(client, fake_smtp):
    fake = fake_smtp()
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert fake.instances == []  # health never touches SMTP
