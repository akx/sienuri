import { Query } from "./types.ts";

function cleanSQL(sql: string): string {
  return sql.trim().replaceAll(/\s+/g, " ");
}

export const queries: Query[] = [
  {
    name: "Suppilovahvero",
    getSQL: (bounds) => {
      const { west, south, east, north } = bounds;
      return cleanSQL(`
      SELECT lon, lat, elevation, tpi_20m, aspect, slope
      FROM topo
      LEFT JOIN stand ON topo.standid = stand.standid
      WHERE 
        lon BETWEEN ${west} AND ${east} AND lat BETWEEN ${south} AND ${north}
        AND tpi_20m < -0.3 AND tpi_20m > -3
        AND elevation > 1
        AND (aspect >= 315 OR aspect <= 45)
        AND slope < 15
        AND stand.maintreespecies IN (1,2,8,10,11,12,16,22,23,30)
      ORDER BY RANDOM()
      LIMIT 20000
    `);
    },
  },
  // {
  //   name: "Laaksoli",
  //   getSQL: (bounds) => {
  //     const { west, south, east, north } = bounds;
  //     return cleanSQL(`
  //     SELECT lon, lat, elevation, aspect
  //     FROM topo
  //     WHERE tpi_30m < -3
  //       AND elevation > 1
  //       AND lon >= ${west} AND lon <= ${east}
  //       AND lat >= ${south} AND lat <= ${north}
  //     ORDER BY RANDOM()
  //     LIMIT 20000
  //   `);
  //   },
  // },
];
