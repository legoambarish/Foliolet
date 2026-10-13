'use strict';
// Small text-only Markdown subset. No HTML, links, images or executable markup accepted.
window.folioletMarkdown=function(target,text){
 target.replaceChildren();for(const line of String(text).split('\n')){const block=document.createElement(line.startsWith('- ')?'li':'p');const content=line.replace(/^- /,'');const pieces=content.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);for(const piece of pieces){if(piece.startsWith('**')&&piece.endsWith('**')){const strong=document.createElement('strong');strong.textContent=piece.slice(2,-2);block.append(strong);}else if(piece.startsWith('`')&&piece.endsWith('`')){const code=document.createElement('code');code.textContent=piece.slice(1,-1);block.append(code);}else block.append(document.createTextNode(piece));}if(block.tagName==='LI'){let list=target.lastElementChild;if(!list||list.tagName!=='UL'){list=document.createElement('ul');target.append(list);}list.append(block);}else target.append(block);}
};
