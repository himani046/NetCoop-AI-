/** Browser-safe basemap configuration. NEVER put OAuth client secrets in NEXT_PUBLIC_* values. */
export const campusBounds:[[number,number],[number,number]]=[[85.666,20.143],[85.683,20.153]];
const osmStyle={version:8 as const,sources:{osm:{type:"raster" as const,tiles:["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],tileSize:256,attribution:"© OpenStreetMap contributors"}},layers:[{id:"osm",type:"raster" as const,source:"osm"}]};
function sentinelWms(){
 const instance=(process.env.NEXT_PUBLIC_SENTINEL_INSTANCE_ID||"").trim();
 if(!/^[a-zA-Z0-9-]{8,120}$/.test(instance))return null;
 const layer=(process.env.NEXT_PUBLIC_SENTINEL_LAYER||"NATURAL-COLOR").trim();
 if(!/^[A-Za-z0-9_-]{1,80}$/.test(layer))return null;
 const endpoint=process.env.NEXT_PUBLIC_SENTINEL_WMS_BASE==="copernicus"?"https://sh.dataspace.copernicus.eu":"https://services.sentinel-hub.com";
 const date=(process.env.NEXT_PUBLIC_SENTINEL_TIME||"").trim();
 const time=/^\d{4}-\d{2}-\d{2}(\/\d{4}-\d{2}-\d{2})?$/.test(date)?"&TIME="+date:"";
 const url=endpoint+"/ogc/wms/"+instance+"?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&LAYERS="+layer+"&SRS=EPSG%3A3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256&FORMAT=image%2Fjpeg&MAXCC=40"+time;
 return {version:8 as const,sources:{sentinel:{type:"raster" as const,tiles:[url],tileSize:256,attribution:"Sentinel Hub / Copernicus satellite data (check your imagery license)" }},layers:[{id:"satellite",type:"raster" as const,source:"sentinel"}]};
}
export function getCampusBasemap(){
 const sentinel=sentinelWms();
 if(sentinel)return {style:sentinel,source:"Sentinel Hub WMS satellite imagery",configured:true};
 const explicit=process.env.NEXT_PUBLIC_SATELLITE_STYLE_URL?.trim();
 if(explicit&&/^https:\/\//.test(explicit))return {style:explicit,source:"Configured licensed imagery style",configured:true};
 const maptiler=process.env.NEXT_PUBLIC_MAPTILER_KEY?.trim();
 if(maptiler)return {style:"https://api.maptiler.com/maps/satellite-v4/style.json?key="+encodeURIComponent(maptiler),source:"MapTiler satellite imagery",configured:true};
 return {style:osmStyle,source:"OpenStreetMap street map (satellite credentials not configured)",configured:false};
}
