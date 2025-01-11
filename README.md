# Delivery-Service

[![IMG-2725.jpg](https://i.postimg.cc/PxsxRhtF/IMG-2725.jpg)](https://postimg.cc/rdjMDBRS)



## Data Models

### User
- Roles: customer, courier, admin
- Authentication via email/password

### Order
- Statuses: new, paid, preparing, assigned_to_courier, in_delivery, delivered, cancelled
- Relationships with customer and courier
- Delivery status tracking

### Courier
- Binding to user
- Availability status
- Current location

### Notification
- Notifications for users
- Binding to orders

## Security

- JWT authentication is used
- Passwords are hashed before saving
- Access rights are differentiated by roles

## Testing

For API testing, you can use:
1. Swagger UI (http://localhost:8000/docs)
2. Postman
3. curl commands

[![IMG-2726.jpg](https://i.postimg.cc/1zNXB4Zq/IMG-2726.jpg)](https://postimg.cc/nspncFrF)


### Creating a client
bash
curl -X POST "http://localhost:8000/customers/" \
-H "Content-Type: application/json" \
-d '{"name":"Ivan","address":"1 Pushkin St.", "phone":"+79001234567","email":"ivan@example.com"}'
### Getting a token
bash
curl -X POST "http://localhost:8000/token" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=user@example.com&password=password123"

## License

MIT License

## Support

If you encounter any problems, please create an issue in the project repository.
