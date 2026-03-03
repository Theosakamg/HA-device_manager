/**
 * Generic CRUD API client.
 *
 * Eliminates the need for separate client classes for each entity type.
 * Entity-specific clients are created by instantiating or extending this class.
 */
import { BaseClient } from "./base-client";

/**
 * Generic CRUD client parameterized by entity type and endpoint.
 *
 * @example
 * ```ts
 * const buildingClient = new CrudClient<DmBuilding>("/buildings");
 * const floors = await floorClient.getAll("?building_id=1");
 * ```
 */
export class CrudClient<T> extends BaseClient {
  /** The API endpoint path segment (e.g. "/homes", "/devices"). */
  private readonly endpoint: string;

  constructor(endpoint: string) {
    super();
    this.endpoint = endpoint;
  }

  /** Get all entities, with an optional raw query string. */
  async getAll(query: string = ""): Promise<T[]> {
    return this.get<T[]>(`${this.endpoint}${query}`);
  }

  /** Get a single entity by ID. */
  async getById(id: number): Promise<T> {
    return this.get<T>(`${this.endpoint}/${id}`);
  }

  /** Create a new entity. */
  async create(data: Partial<T>): Promise<T> {
    return this.post<T>(this.endpoint, data);
  }

  /** Update an existing entity. */
  async update(id: number, data: Partial<T>): Promise<T> {
    return this.put<T>(`${this.endpoint}/${id}`, data);
  }

  /** Delete an entity by ID. */
  async remove(id: number): Promise<void> {
    await this.del(`${this.endpoint}/${id}`);
  }
}
