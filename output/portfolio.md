# Portfolio

Currently focused on building robust APIs and exploring software architecture patterns for scalable systems. Passionate about clean architecture, domain-driven design, and AI-augmented development workflows.

## What I Build

- Backend frameworks, API scaffolds, and reusable developer templates.

## Ignix Core

TypeScript package for building type-safe, extensible services with Result pattern and ORM-agnostic repositories

**Tech:** TypeScript

[View Project](https://github.com/JohnyYen/ignix-core)

- Implements Result pattern for explicit success/failure handling, improving reliability
- Provides generic services (IService<T>) with CRUD operations and customizable DTOs
- ORM-agnostic repository interface supporting TypeORM, Prisma, and Sequelize
- Framework-flexible API handlers with adapters for NestJS, Express, Fastify, and Hono
- Promotes SOLID principles and type safety to reduce bugs and improve maintainability

## FastAPI Generic Scaffold

A fully generic FastAPI scaffold architected with Screaming Architecture and Clean Architecture, featuring an automated scaffolding script that generates complete, production-ready modules — repository, service, and API layers — out of the box. The generic core is extensible through a Builder pattern, allowing custom wrappers at any layer, making it adaptable to virtually any backend domain. Includes a customizable built-in admin panel.

**Tech:** Python

[View Project](https://github.com/JohnyYen/extreme-fastapi-boilerplate)

- Architected with Screaming Architecture and Clean Architecture for domain-driven module organization
- Automated scaffolding script generates ready-to-use modules with full repository, service, and API layers
- Extensible core with Builder pattern for adding custom wrappers at repo, service, or controller level
- Built-in customizable admin panel
- Designed for adaptability across any backend domain

## NestJS Boilerplate

Complete boilerplate for NestJS projects with Prisma ORM

**Tech:** TypeScript

[View Project](https://github.com/JohnyYen/NestJs-Template)

- Modular and scalable architecture with organized folder structure
- Integrated Prisma ORM configuration with migrations and seeding
- Generic base controllers, services, and repositories
- Centralized app configuration and DTOs for pagination/responses
- Production-ready setup with Swagger auto-documentation
- Custom exception handling and decorators

## FastAPI Template

Base template for creating fast, scalable APIs with FastAPI

**Tech:** Python

[View Project](https://github.com/JohnyYen/fastapi-template)

- JWT authentication integrated
- SQLAlchemy async configuration with Alembic migrations
- Pydantic schemas for data validation
- Complete CRUD implementation with Repository pattern
- Testing configuration with pytest
- Docker and Docker Compose ready for deployment
- Automatic documentation with Swagger UI and ReDoc
