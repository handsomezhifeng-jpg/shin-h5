// Geometry, UVs and original data remain owned by the native board. Only image sources vary.
const original=typeof location!=='undefined'&&new URLSearchParams(location.search).get('boardSkin')==='original';
export const BOARD_SKIN={id:original?'original':'sanguo-v1',textures:original?{}:{
 'assets/scene/grid-atlas.png':'assets/scene/skins/sanguo/grid-atlas-v1.png',
 'assets/scene/grid-atlas-goldcoin.png':'assets/scene/skins/sanguo/grid-atlas-goldcoin-v1.png',
 'assets/scene/grid-props/checkerboard_goldcoin_01_d.png':'assets/scene/skins/sanguo/grid-atlas-goldcoin-v1.png'
}};
export const boardTextureURL=url=>BOARD_SKIN.textures[url]||url;
