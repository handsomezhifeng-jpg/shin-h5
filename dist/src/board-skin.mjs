// Native board data stays intact; skin-specific adaptations live in their own renderer.
const requested=typeof location==='undefined'?'sanguo':new URLSearchParams(location.search).get('boardSkin');
const original=requested==='original',version=requested==='v1'?'v1':'v2';
export const BOARD_SKIN={id:original?'original':'sanguo-'+version,environment:!original&&version==='v2',textures:original?{}:{
 'assets/scene/grid-atlas.png':`assets/scene/skins/sanguo/grid-atlas-${version}.png`,
 'assets/scene/grid-atlas-goldcoin.png':`assets/scene/skins/sanguo/grid-atlas-goldcoin-${version}.png`,
 'assets/scene/grid-props/checkerboard_goldcoin_01_d.png':`assets/scene/skins/sanguo/grid-atlas-goldcoin-${version}.png`
}};
export const boardTextureURL=url=>BOARD_SKIN.textures[url]||url;
