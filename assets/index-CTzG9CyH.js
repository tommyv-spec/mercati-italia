const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["./MarketsMap-DocHHfX7.js","./MarketsMap-MG_XUJyD.css"])))=>i.map(i=>d[i]);
(function(){const c=document.createElement("link").relList;if(c&&c.supports&&c.supports("modulepreload"))return;for(const g of document.querySelectorAll('link[rel="modulepreload"]'))f(g);new MutationObserver(g=>{for(const x of g)if(x.type==="childList")for(const k of x.addedNodes)k.tagName==="LINK"&&k.rel==="modulepreload"&&f(k)}).observe(document,{childList:!0,subtree:!0});function u(g){const x={};return g.integrity&&(x.integrity=g.integrity),g.referrerPolicy&&(x.referrerPolicy=g.referrerPolicy),g.crossOrigin==="use-credentials"?x.credentials="include":g.crossOrigin==="anonymous"?x.credentials="omit":x.credentials="same-origin",x}function f(g){if(g.ep)return;g.ep=!0;const x=u(g);fetch(g.href,x)}})();function Yc(o){return o&&o.__esModule&&Object.prototype.hasOwnProperty.call(o,"default")?o.default:o}var Ia={exports:{}},Si={},Aa={exports:{}},ue={};/**
 * @license React
 * react.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var jc;function Jf(){if(jc)return ue;jc=1;var o=Symbol.for("react.element"),c=Symbol.for("react.portal"),u=Symbol.for("react.fragment"),f=Symbol.for("react.strict_mode"),g=Symbol.for("react.profiler"),x=Symbol.for("react.provider"),k=Symbol.for("react.context"),N=Symbol.for("react.forward_ref"),F=Symbol.for("react.suspense"),X=Symbol.for("react.memo"),G=Symbol.for("react.lazy"),q=Symbol.iterator;function te(v){return v===null||typeof v!="object"?null:(v=q&&v[q]||v["@@iterator"],typeof v=="function"?v:null)}var _={isMounted:function(){return!1},enqueueForceUpdate:function(){},enqueueReplaceState:function(){},enqueueSetState:function(){}},E=Object.assign,M={};function K(v,j,oe){this.props=v,this.context=j,this.refs=M,this.updater=oe||_}K.prototype.isReactComponent={},K.prototype.setState=function(v,j){if(typeof v!="object"&&typeof v!="function"&&v!=null)throw Error("setState(...): takes an object of state variables to update or a function which returns an object of state variables.");this.updater.enqueueSetState(this,v,j,"setState")},K.prototype.forceUpdate=function(v){this.updater.enqueueForceUpdate(this,v,"forceUpdate")};function Z(){}Z.prototype=K.prototype;function ae(v,j,oe){this.props=v,this.context=j,this.refs=M,this.updater=oe||_}var ze=ae.prototype=new Z;ze.constructor=ae,E(ze,K.prototype),ze.isPureReactComponent=!0;var pe=Array.isArray,Me=Object.prototype.hasOwnProperty,he={current:null},_e={key:!0,ref:!0,__self:!0,__source:!0};function Ue(v,j,oe){var le,ce={},de=null,xe=null;if(j!=null)for(le in j.ref!==void 0&&(xe=j.ref),j.key!==void 0&&(de=""+j.key),j)Me.call(j,le)&&!_e.hasOwnProperty(le)&&(ce[le]=j[le]);var ge=arguments.length-2;if(ge===1)ce.children=oe;else if(1<ge){for(var je=Array(ge),Ge=0;Ge<ge;Ge++)je[Ge]=arguments[Ge+2];ce.children=je}if(v&&v.defaultProps)for(le in ge=v.defaultProps,ge)ce[le]===void 0&&(ce[le]=ge[le]);return{$$typeof:o,type:v,key:de,ref:xe,props:ce,_owner:he.current}}function He(v,j){return{$$typeof:o,type:v.type,key:j,ref:v.ref,props:v.props,_owner:v._owner}}function qe(v){return typeof v=="object"&&v!==null&&v.$$typeof===o}function nt(v){var j={"=":"=0",":":"=2"};return"$"+v.replace(/[=:]/g,function(oe){return j[oe]})}var H=/\/+/g;function B(v,j){return typeof v=="object"&&v!==null&&v.key!=null?nt(""+v.key):j.toString(36)}function ne(v,j,oe,le,ce){var de=typeof v;(de==="undefined"||de==="boolean")&&(v=null);var xe=!1;if(v===null)xe=!0;else switch(de){case"string":case"number":xe=!0;break;case"object":switch(v.$$typeof){case o:case c:xe=!0}}if(xe)return xe=v,ce=ce(xe),v=le===""?"."+B(xe,0):le,pe(ce)?(oe="",v!=null&&(oe=v.replace(H,"$&/")+"/"),ne(ce,j,oe,"",function(Ge){return Ge})):ce!=null&&(qe(ce)&&(ce=He(ce,oe+(!ce.key||xe&&xe.key===ce.key?"":(""+ce.key).replace(H,"$&/")+"/")+v)),j.push(ce)),1;if(xe=0,le=le===""?".":le+":",pe(v))for(var ge=0;ge<v.length;ge++){de=v[ge];var je=le+B(de,ge);xe+=ne(de,j,oe,je,ce)}else if(je=te(v),typeof je=="function")for(v=je.call(v),ge=0;!(de=v.next()).done;)de=de.value,je=le+B(de,ge++),xe+=ne(de,j,oe,je,ce);else if(de==="object")throw j=String(v),Error("Objects are not valid as a React child (found: "+(j==="[object Object]"?"object with keys {"+Object.keys(v).join(", ")+"}":j)+"). If you meant to render a collection of children, use an array instead.");return xe}function se(v,j,oe){if(v==null)return v;var le=[],ce=0;return ne(v,le,"","",function(de){return j.call(oe,de,ce++)}),le}function ye(v){if(v._status===-1){var j=v._result;j=j(),j.then(function(oe){(v._status===0||v._status===-1)&&(v._status=1,v._result=oe)},function(oe){(v._status===0||v._status===-1)&&(v._status=2,v._result=oe)}),v._status===-1&&(v._status=0,v._result=j)}if(v._status===1)return v._result.default;throw v._result}var ie={current:null},T={transition:null},A={ReactCurrentDispatcher:ie,ReactCurrentBatchConfig:T,ReactCurrentOwner:he};function $(){throw Error("act(...) is not supported in production builds of React.")}return ue.Children={map:se,forEach:function(v,j,oe){se(v,function(){j.apply(this,arguments)},oe)},count:function(v){var j=0;return se(v,function(){j++}),j},toArray:function(v){return se(v,function(j){return j})||[]},only:function(v){if(!qe(v))throw Error("React.Children.only expected to receive a single React element child.");return v}},ue.Component=K,ue.Fragment=u,ue.Profiler=g,ue.PureComponent=ae,ue.StrictMode=f,ue.Suspense=F,ue.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED=A,ue.act=$,ue.cloneElement=function(v,j,oe){if(v==null)throw Error("React.cloneElement(...): The argument must be a React element, but you passed "+v+".");var le=E({},v.props),ce=v.key,de=v.ref,xe=v._owner;if(j!=null){if(j.ref!==void 0&&(de=j.ref,xe=he.current),j.key!==void 0&&(ce=""+j.key),v.type&&v.type.defaultProps)var ge=v.type.defaultProps;for(je in j)Me.call(j,je)&&!_e.hasOwnProperty(je)&&(le[je]=j[je]===void 0&&ge!==void 0?ge[je]:j[je])}var je=arguments.length-2;if(je===1)le.children=oe;else if(1<je){ge=Array(je);for(var Ge=0;Ge<je;Ge++)ge[Ge]=arguments[Ge+2];le.children=ge}return{$$typeof:o,type:v.type,key:ce,ref:de,props:le,_owner:xe}},ue.createContext=function(v){return v={$$typeof:k,_currentValue:v,_currentValue2:v,_threadCount:0,Provider:null,Consumer:null,_defaultValue:null,_globalName:null},v.Provider={$$typeof:x,_context:v},v.Consumer=v},ue.createElement=Ue,ue.createFactory=function(v){var j=Ue.bind(null,v);return j.type=v,j},ue.createRef=function(){return{current:null}},ue.forwardRef=function(v){return{$$typeof:N,render:v}},ue.isValidElement=qe,ue.lazy=function(v){return{$$typeof:G,_payload:{_status:-1,_result:v},_init:ye}},ue.memo=function(v,j){return{$$typeof:X,type:v,compare:j===void 0?null:j}},ue.startTransition=function(v){var j=T.transition;T.transition={};try{v()}finally{T.transition=j}},ue.unstable_act=$,ue.useCallback=function(v,j){return ie.current.useCallback(v,j)},ue.useContext=function(v){return ie.current.useContext(v)},ue.useDebugValue=function(){},ue.useDeferredValue=function(v){return ie.current.useDeferredValue(v)},ue.useEffect=function(v,j){return ie.current.useEffect(v,j)},ue.useId=function(){return ie.current.useId()},ue.useImperativeHandle=function(v,j,oe){return ie.current.useImperativeHandle(v,j,oe)},ue.useInsertionEffect=function(v,j){return ie.current.useInsertionEffect(v,j)},ue.useLayoutEffect=function(v,j){return ie.current.useLayoutEffect(v,j)},ue.useMemo=function(v,j){return ie.current.useMemo(v,j)},ue.useReducer=function(v,j,oe){return ie.current.useReducer(v,j,oe)},ue.useRef=function(v){return ie.current.useRef(v)},ue.useState=function(v){return ie.current.useState(v)},ue.useSyncExternalStore=function(v,j,oe){return ie.current.useSyncExternalStore(v,j,oe)},ue.useTransition=function(){return ie.current.useTransition()},ue.version="18.3.1",ue}var zc;function qa(){return zc||(zc=1,Aa.exports=Jf()),Aa.exports}/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var Nc;function ep(){if(Nc)return Si;Nc=1;var o=qa(),c=Symbol.for("react.element"),u=Symbol.for("react.fragment"),f=Object.prototype.hasOwnProperty,g=o.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner,x={key:!0,ref:!0,__self:!0,__source:!0};function k(N,F,X){var G,q={},te=null,_=null;X!==void 0&&(te=""+X),F.key!==void 0&&(te=""+F.key),F.ref!==void 0&&(_=F.ref);for(G in F)f.call(F,G)&&!x.hasOwnProperty(G)&&(q[G]=F[G]);if(N&&N.defaultProps)for(G in F=N.defaultProps,F)q[G]===void 0&&(q[G]=F[G]);return{$$typeof:c,type:N,key:te,ref:_,props:q,_owner:g.current}}return Si.Fragment=u,Si.jsx=k,Si.jsxs=k,Si}var Cc;function tp(){return Cc||(Cc=1,Ia.exports=ep()),Ia.exports}var a=tp(),U=qa();const np=Yc(U);var Go={},ba={exports:{}},ht={},Ua={exports:{}},$a={};/**
 * @license React
 * scheduler.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var Ec;function rp(){return Ec||(Ec=1,(function(o){function c(T,A){var $=T.length;T.push(A);e:for(;0<$;){var v=$-1>>>1,j=T[v];if(0<g(j,A))T[v]=A,T[$]=j,$=v;else break e}}function u(T){return T.length===0?null:T[0]}function f(T){if(T.length===0)return null;var A=T[0],$=T.pop();if($!==A){T[0]=$;e:for(var v=0,j=T.length,oe=j>>>1;v<oe;){var le=2*(v+1)-1,ce=T[le],de=le+1,xe=T[de];if(0>g(ce,$))de<j&&0>g(xe,ce)?(T[v]=xe,T[de]=$,v=de):(T[v]=ce,T[le]=$,v=le);else if(de<j&&0>g(xe,$))T[v]=xe,T[de]=$,v=de;else break e}}return A}function g(T,A){var $=T.sortIndex-A.sortIndex;return $!==0?$:T.id-A.id}if(typeof performance=="object"&&typeof performance.now=="function"){var x=performance;o.unstable_now=function(){return x.now()}}else{var k=Date,N=k.now();o.unstable_now=function(){return k.now()-N}}var F=[],X=[],G=1,q=null,te=3,_=!1,E=!1,M=!1,K=typeof setTimeout=="function"?setTimeout:null,Z=typeof clearTimeout=="function"?clearTimeout:null,ae=typeof setImmediate<"u"?setImmediate:null;typeof navigator<"u"&&navigator.scheduling!==void 0&&navigator.scheduling.isInputPending!==void 0&&navigator.scheduling.isInputPending.bind(navigator.scheduling);function ze(T){for(var A=u(X);A!==null;){if(A.callback===null)f(X);else if(A.startTime<=T)f(X),A.sortIndex=A.expirationTime,c(F,A);else break;A=u(X)}}function pe(T){if(M=!1,ze(T),!E)if(u(F)!==null)E=!0,ye(Me);else{var A=u(X);A!==null&&ie(pe,A.startTime-T)}}function Me(T,A){E=!1,M&&(M=!1,Z(Ue),Ue=-1),_=!0;var $=te;try{for(ze(A),q=u(F);q!==null&&(!(q.expirationTime>A)||T&&!nt());){var v=q.callback;if(typeof v=="function"){q.callback=null,te=q.priorityLevel;var j=v(q.expirationTime<=A);A=o.unstable_now(),typeof j=="function"?q.callback=j:q===u(F)&&f(F),ze(A)}else f(F);q=u(F)}if(q!==null)var oe=!0;else{var le=u(X);le!==null&&ie(pe,le.startTime-A),oe=!1}return oe}finally{q=null,te=$,_=!1}}var he=!1,_e=null,Ue=-1,He=5,qe=-1;function nt(){return!(o.unstable_now()-qe<He)}function H(){if(_e!==null){var T=o.unstable_now();qe=T;var A=!0;try{A=_e(!0,T)}finally{A?B():(he=!1,_e=null)}}else he=!1}var B;if(typeof ae=="function")B=function(){ae(H)};else if(typeof MessageChannel<"u"){var ne=new MessageChannel,se=ne.port2;ne.port1.onmessage=H,B=function(){se.postMessage(null)}}else B=function(){K(H,0)};function ye(T){_e=T,he||(he=!0,B())}function ie(T,A){Ue=K(function(){T(o.unstable_now())},A)}o.unstable_IdlePriority=5,o.unstable_ImmediatePriority=1,o.unstable_LowPriority=4,o.unstable_NormalPriority=3,o.unstable_Profiling=null,o.unstable_UserBlockingPriority=2,o.unstable_cancelCallback=function(T){T.callback=null},o.unstable_continueExecution=function(){E||_||(E=!0,ye(Me))},o.unstable_forceFrameRate=function(T){0>T||125<T?console.error("forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported"):He=0<T?Math.floor(1e3/T):5},o.unstable_getCurrentPriorityLevel=function(){return te},o.unstable_getFirstCallbackNode=function(){return u(F)},o.unstable_next=function(T){switch(te){case 1:case 2:case 3:var A=3;break;default:A=te}var $=te;te=A;try{return T()}finally{te=$}},o.unstable_pauseExecution=function(){},o.unstable_requestPaint=function(){},o.unstable_runWithPriority=function(T,A){switch(T){case 1:case 2:case 3:case 4:case 5:break;default:T=3}var $=te;te=T;try{return A()}finally{te=$}},o.unstable_scheduleCallback=function(T,A,$){var v=o.unstable_now();switch(typeof $=="object"&&$!==null?($=$.delay,$=typeof $=="number"&&0<$?v+$:v):$=v,T){case 1:var j=-1;break;case 2:j=250;break;case 5:j=1073741823;break;case 4:j=1e4;break;default:j=5e3}return j=$+j,T={id:G++,callback:A,priorityLevel:T,startTime:$,expirationTime:j,sortIndex:-1},$>v?(T.sortIndex=$,c(X,T),u(F)===null&&T===u(X)&&(M?(Z(Ue),Ue=-1):M=!0,ie(pe,$-v))):(T.sortIndex=j,c(F,T),E||_||(E=!0,ye(Me))),T},o.unstable_shouldYield=nt,o.unstable_wrapCallback=function(T){var A=te;return function(){var $=te;te=A;try{return T.apply(this,arguments)}finally{te=$}}}})($a)),$a}var Dc;function ip(){return Dc||(Dc=1,Ua.exports=rp()),Ua.exports}/**
 * @license React
 * react-dom.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var Lc;function op(){if(Lc)return ht;Lc=1;var o=qa(),c=ip();function u(e){for(var t="https://reactjs.org/docs/error-decoder.html?invariant="+e,n=1;n<arguments.length;n++)t+="&args[]="+encodeURIComponent(arguments[n]);return"Minified React error #"+e+"; visit "+t+" for the full message or use the non-minified dev environment for full errors and additional helpful warnings."}var f=new Set,g={};function x(e,t){k(e,t),k(e+"Capture",t)}function k(e,t){for(g[e]=t,e=0;e<t.length;e++)f.add(t[e])}var N=!(typeof window>"u"||typeof window.document>"u"||typeof window.document.createElement>"u"),F=Object.prototype.hasOwnProperty,X=/^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/,G={},q={};function te(e){return F.call(q,e)?!0:F.call(G,e)?!1:X.test(e)?q[e]=!0:(G[e]=!0,!1)}function _(e,t,n,r){if(n!==null&&n.type===0)return!1;switch(typeof t){case"function":case"symbol":return!0;case"boolean":return r?!1:n!==null?!n.acceptsBooleans:(e=e.toLowerCase().slice(0,5),e!=="data-"&&e!=="aria-");default:return!1}}function E(e,t,n,r){if(t===null||typeof t>"u"||_(e,t,n,r))return!0;if(r)return!1;if(n!==null)switch(n.type){case 3:return!t;case 4:return t===!1;case 5:return isNaN(t);case 6:return isNaN(t)||1>t}return!1}function M(e,t,n,r,i,l,s){this.acceptsBooleans=t===2||t===3||t===4,this.attributeName=r,this.attributeNamespace=i,this.mustUseProperty=n,this.propertyName=e,this.type=t,this.sanitizeURL=l,this.removeEmptyString=s}var K={};"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style".split(" ").forEach(function(e){K[e]=new M(e,0,!1,e,null,!1,!1)}),[["acceptCharset","accept-charset"],["className","class"],["htmlFor","for"],["httpEquiv","http-equiv"]].forEach(function(e){var t=e[0];K[t]=new M(t,1,!1,e[1],null,!1,!1)}),["contentEditable","draggable","spellCheck","value"].forEach(function(e){K[e]=new M(e,2,!1,e.toLowerCase(),null,!1,!1)}),["autoReverse","externalResourcesRequired","focusable","preserveAlpha"].forEach(function(e){K[e]=new M(e,2,!1,e,null,!1,!1)}),"allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope".split(" ").forEach(function(e){K[e]=new M(e,3,!1,e.toLowerCase(),null,!1,!1)}),["checked","multiple","muted","selected"].forEach(function(e){K[e]=new M(e,3,!0,e,null,!1,!1)}),["capture","download"].forEach(function(e){K[e]=new M(e,4,!1,e,null,!1,!1)}),["cols","rows","size","span"].forEach(function(e){K[e]=new M(e,6,!1,e,null,!1,!1)}),["rowSpan","start"].forEach(function(e){K[e]=new M(e,5,!1,e.toLowerCase(),null,!1,!1)});var Z=/[\-:]([a-z])/g;function ae(e){return e[1].toUpperCase()}"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height".split(" ").forEach(function(e){var t=e.replace(Z,ae);K[t]=new M(t,1,!1,e,null,!1,!1)}),"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type".split(" ").forEach(function(e){var t=e.replace(Z,ae);K[t]=new M(t,1,!1,e,"http://www.w3.org/1999/xlink",!1,!1)}),["xml:base","xml:lang","xml:space"].forEach(function(e){var t=e.replace(Z,ae);K[t]=new M(t,1,!1,e,"http://www.w3.org/XML/1998/namespace",!1,!1)}),["tabIndex","crossOrigin"].forEach(function(e){K[e]=new M(e,1,!1,e.toLowerCase(),null,!1,!1)}),K.xlinkHref=new M("xlinkHref",1,!1,"xlink:href","http://www.w3.org/1999/xlink",!0,!1),["src","href","action","formAction"].forEach(function(e){K[e]=new M(e,1,!1,e.toLowerCase(),null,!0,!0)});function ze(e,t,n,r){var i=K.hasOwnProperty(t)?K[t]:null;(i!==null?i.type!==0:r||!(2<t.length)||t[0]!=="o"&&t[0]!=="O"||t[1]!=="n"&&t[1]!=="N")&&(E(t,n,i,r)&&(n=null),r||i===null?te(t)&&(n===null?e.removeAttribute(t):e.setAttribute(t,""+n)):i.mustUseProperty?e[i.propertyName]=n===null?i.type===3?!1:"":n:(t=i.attributeName,r=i.attributeNamespace,n===null?e.removeAttribute(t):(i=i.type,n=i===3||i===4&&n===!0?"":""+n,r?e.setAttributeNS(r,t,n):e.setAttribute(t,n))))}var pe=o.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED,Me=Symbol.for("react.element"),he=Symbol.for("react.portal"),_e=Symbol.for("react.fragment"),Ue=Symbol.for("react.strict_mode"),He=Symbol.for("react.profiler"),qe=Symbol.for("react.provider"),nt=Symbol.for("react.context"),H=Symbol.for("react.forward_ref"),B=Symbol.for("react.suspense"),ne=Symbol.for("react.suspense_list"),se=Symbol.for("react.memo"),ye=Symbol.for("react.lazy"),ie=Symbol.for("react.offscreen"),T=Symbol.iterator;function A(e){return e===null||typeof e!="object"?null:(e=T&&e[T]||e["@@iterator"],typeof e=="function"?e:null)}var $=Object.assign,v;function j(e){if(v===void 0)try{throw Error()}catch(n){var t=n.stack.trim().match(/\n( *(at )?)/);v=t&&t[1]||""}return`
`+v+e}var oe=!1;function le(e,t){if(!e||oe)return"";oe=!0;var n=Error.prepareStackTrace;Error.prepareStackTrace=void 0;try{if(t)if(t=function(){throw Error()},Object.defineProperty(t.prototype,"props",{set:function(){throw Error()}}),typeof Reflect=="object"&&Reflect.construct){try{Reflect.construct(t,[])}catch(S){var r=S}Reflect.construct(e,[],t)}else{try{t.call()}catch(S){r=S}e.call(t.prototype)}else{try{throw Error()}catch(S){r=S}e()}}catch(S){if(S&&r&&typeof S.stack=="string"){for(var i=S.stack.split(`
`),l=r.stack.split(`
`),s=i.length-1,d=l.length-1;1<=s&&0<=d&&i[s]!==l[d];)d--;for(;1<=s&&0<=d;s--,d--)if(i[s]!==l[d]){if(s!==1||d!==1)do if(s--,d--,0>d||i[s]!==l[d]){var p=`
`+i[s].replace(" at new "," at ");return e.displayName&&p.includes("<anonymous>")&&(p=p.replace("<anonymous>",e.displayName)),p}while(1<=s&&0<=d);break}}}finally{oe=!1,Error.prepareStackTrace=n}return(e=e?e.displayName||e.name:"")?j(e):""}function ce(e){switch(e.tag){case 5:return j(e.type);case 16:return j("Lazy");case 13:return j("Suspense");case 19:return j("SuspenseList");case 0:case 2:case 15:return e=le(e.type,!1),e;case 11:return e=le(e.type.render,!1),e;case 1:return e=le(e.type,!0),e;default:return""}}function de(e){if(e==null)return null;if(typeof e=="function")return e.displayName||e.name||null;if(typeof e=="string")return e;switch(e){case _e:return"Fragment";case he:return"Portal";case He:return"Profiler";case Ue:return"StrictMode";case B:return"Suspense";case ne:return"SuspenseList"}if(typeof e=="object")switch(e.$$typeof){case nt:return(e.displayName||"Context")+".Consumer";case qe:return(e._context.displayName||"Context")+".Provider";case H:var t=e.render;return e=e.displayName,e||(e=t.displayName||t.name||"",e=e!==""?"ForwardRef("+e+")":"ForwardRef"),e;case se:return t=e.displayName||null,t!==null?t:de(e.type)||"Memo";case ye:t=e._payload,e=e._init;try{return de(e(t))}catch{}}return null}function xe(e){var t=e.type;switch(e.tag){case 24:return"Cache";case 9:return(t.displayName||"Context")+".Consumer";case 10:return(t._context.displayName||"Context")+".Provider";case 18:return"DehydratedFragment";case 11:return e=t.render,e=e.displayName||e.name||"",t.displayName||(e!==""?"ForwardRef("+e+")":"ForwardRef");case 7:return"Fragment";case 5:return t;case 4:return"Portal";case 3:return"Root";case 6:return"Text";case 16:return de(t);case 8:return t===Ue?"StrictMode":"Mode";case 22:return"Offscreen";case 12:return"Profiler";case 21:return"Scope";case 13:return"Suspense";case 19:return"SuspenseList";case 25:return"TracingMarker";case 1:case 0:case 17:case 2:case 14:case 15:if(typeof t=="function")return t.displayName||t.name||null;if(typeof t=="string")return t}return null}function ge(e){switch(typeof e){case"boolean":case"number":case"string":case"undefined":return e;case"object":return e;default:return""}}function je(e){var t=e.type;return(e=e.nodeName)&&e.toLowerCase()==="input"&&(t==="checkbox"||t==="radio")}function Ge(e){var t=je(e)?"checked":"value",n=Object.getOwnPropertyDescriptor(e.constructor.prototype,t),r=""+e[t];if(!e.hasOwnProperty(t)&&typeof n<"u"&&typeof n.get=="function"&&typeof n.set=="function"){var i=n.get,l=n.set;return Object.defineProperty(e,t,{configurable:!0,get:function(){return i.call(this)},set:function(s){r=""+s,l.call(this,s)}}),Object.defineProperty(e,t,{enumerable:n.enumerable}),{getValue:function(){return r},setValue:function(s){r=""+s},stopTracking:function(){e._valueTracker=null,delete e[t]}}}}function lt(e){e._valueTracker||(e._valueTracker=Ge(e))}function On(e){if(!e)return!1;var t=e._valueTracker;if(!t)return!0;var n=t.getValue(),r="";return e&&(r=je(e)?e.checked?"true":"false":e.value),e=r,e!==n?(t.setValue(e),!0):!1}function $e(e){if(e=e||(typeof document<"u"?document:void 0),typeof e>"u")return null;try{return e.activeElement||e.body}catch{return e.body}}function Rt(e,t){var n=t.checked;return $({},t,{defaultChecked:void 0,defaultValue:void 0,value:void 0,checked:n??e._wrapperState.initialChecked})}function Xe(e,t){var n=t.defaultValue==null?"":t.defaultValue,r=t.checked!=null?t.checked:t.defaultChecked;n=ge(t.value!=null?t.value:n),e._wrapperState={initialChecked:r,initialValue:n,controlled:t.type==="checkbox"||t.type==="radio"?t.checked!=null:t.value!=null}}function Ot(e,t){t=t.checked,t!=null&&ze(e,"checked",t,!1)}function jt(e,t){Ot(e,t);var n=ge(t.value),r=t.type;if(n!=null)r==="number"?(n===0&&e.value===""||e.value!=n)&&(e.value=""+n):e.value!==""+n&&(e.value=""+n);else if(r==="submit"||r==="reset"){e.removeAttribute("value");return}t.hasOwnProperty("value")?zt(e,t.type,n):t.hasOwnProperty("defaultValue")&&zt(e,t.type,ge(t.defaultValue)),t.checked==null&&t.defaultChecked!=null&&(e.defaultChecked=!!t.defaultChecked)}function Gt(e,t,n){if(t.hasOwnProperty("value")||t.hasOwnProperty("defaultValue")){var r=t.type;if(!(r!=="submit"&&r!=="reset"||t.value!==void 0&&t.value!==null))return;t=""+e._wrapperState.initialValue,n||t===e.value||(e.value=t),e.defaultValue=t}n=e.name,n!==""&&(e.name=""),e.defaultChecked=!!e._wrapperState.initialChecked,n!==""&&(e.name=n)}function zt(e,t,n){(t!=="number"||$e(e.ownerDocument)!==e)&&(n==null?e.defaultValue=""+e._wrapperState.initialValue:e.defaultValue!==""+n&&(e.defaultValue=""+n))}var It=Array.isArray;function gt(e,t,n,r){if(e=e.options,t){t={};for(var i=0;i<n.length;i++)t["$"+n[i]]=!0;for(n=0;n<e.length;n++)i=t.hasOwnProperty("$"+e[n].value),e[n].selected!==i&&(e[n].selected=i),i&&r&&(e[n].defaultSelected=!0)}else{for(n=""+ge(n),t=null,i=0;i<e.length;i++){if(e[i].value===n){e[i].selected=!0,r&&(e[i].defaultSelected=!0);return}t!==null||e[i].disabled||(t=e[i])}t!==null&&(t.selected=!0)}}function at(e,t){if(t.dangerouslySetInnerHTML!=null)throw Error(u(91));return $({},t,{value:void 0,defaultValue:void 0,children:""+e._wrapperState.initialValue})}function or(e,t){var n=t.value;if(n==null){if(n=t.children,t=t.defaultValue,n!=null){if(t!=null)throw Error(u(92));if(It(n)){if(1<n.length)throw Error(u(93));n=n[0]}t=n}t==null&&(t=""),n=t}e._wrapperState={initialValue:ge(n)}}function lr(e,t){var n=ge(t.value),r=ge(t.defaultValue);n!=null&&(n=""+n,n!==e.value&&(e.value=n),t.defaultValue==null&&e.defaultValue!==n&&(e.defaultValue=n)),r!=null&&(e.defaultValue=""+r)}function fn(e){var t=e.textContent;t===e._wrapperState.initialValue&&t!==""&&t!==null&&(e.value=t)}function ar(e){switch(e){case"svg":return"http://www.w3.org/2000/svg";case"math":return"http://www.w3.org/1998/Math/MathML";default:return"http://www.w3.org/1999/xhtml"}}function In(e,t){return e==null||e==="http://www.w3.org/1999/xhtml"?ar(t):e==="http://www.w3.org/2000/svg"&&t==="foreignObject"?"http://www.w3.org/1999/xhtml":e}var Xt,An=(function(e){return typeof MSApp<"u"&&MSApp.execUnsafeLocalFunction?function(t,n,r,i){MSApp.execUnsafeLocalFunction(function(){return e(t,n,r,i)})}:e})(function(e,t){if(e.namespaceURI!=="http://www.w3.org/2000/svg"||"innerHTML"in e)e.innerHTML=t;else{for(Xt=Xt||document.createElement("div"),Xt.innerHTML="<svg>"+t.valueOf().toString()+"</svg>",t=Xt.firstChild;e.firstChild;)e.removeChild(e.firstChild);for(;t.firstChild;)e.appendChild(t.firstChild)}});function Zt(e,t){if(t){var n=e.firstChild;if(n&&n===e.lastChild&&n.nodeType===3){n.nodeValue=t;return}}e.textContent=t}var mt={animationIterationCount:!0,aspectRatio:!0,borderImageOutset:!0,borderImageSlice:!0,borderImageWidth:!0,boxFlex:!0,boxFlexGroup:!0,boxOrdinalGroup:!0,columnCount:!0,columns:!0,flex:!0,flexGrow:!0,flexPositive:!0,flexShrink:!0,flexNegative:!0,flexOrder:!0,gridArea:!0,gridRow:!0,gridRowEnd:!0,gridRowSpan:!0,gridRowStart:!0,gridColumn:!0,gridColumnEnd:!0,gridColumnSpan:!0,gridColumnStart:!0,fontWeight:!0,lineClamp:!0,lineHeight:!0,opacity:!0,order:!0,orphans:!0,tabSize:!0,widows:!0,zIndex:!0,zoom:!0,fillOpacity:!0,floodOpacity:!0,stopOpacity:!0,strokeDasharray:!0,strokeDashoffset:!0,strokeMiterlimit:!0,strokeOpacity:!0,strokeWidth:!0},bn=["Webkit","ms","Moz","O"];Object.keys(mt).forEach(function(e){bn.forEach(function(t){t=t+e.charAt(0).toUpperCase()+e.substring(1),mt[t]=mt[e]})});function Ir(e,t,n){return t==null||typeof t=="boolean"||t===""?"":n||typeof t!="number"||t===0||mt.hasOwnProperty(e)&&mt[e]?(""+t).trim():t+"px"}function Mi(e,t){e=e.style;for(var n in t)if(t.hasOwnProperty(n)){var r=n.indexOf("--")===0,i=Ir(n,t[n],r);n==="float"&&(n="cssFloat"),r?e.setProperty(n,i):e[n]=i}}var es=$({menuitem:!0},{area:!0,base:!0,br:!0,col:!0,embed:!0,hr:!0,img:!0,input:!0,keygen:!0,link:!0,meta:!0,param:!0,source:!0,track:!0,wbr:!0});function Fi(e,t){if(t){if(es[e]&&(t.children!=null||t.dangerouslySetInnerHTML!=null))throw Error(u(137,e));if(t.dangerouslySetInnerHTML!=null){if(t.children!=null)throw Error(u(60));if(typeof t.dangerouslySetInnerHTML!="object"||!("__html"in t.dangerouslySetInnerHTML))throw Error(u(61))}if(t.style!=null&&typeof t.style!="object")throw Error(u(62))}}function Ar(e,t){if(e.indexOf("-")===-1)return typeof t.is=="string";switch(e){case"annotation-xml":case"color-profile":case"font-face":case"font-face-src":case"font-face-uri":case"font-face-format":case"font-face-name":case"missing-glyph":return!1;default:return!0}}var Un=null;function $n(e){return e=e.target||e.srcElement||window,e.correspondingUseElement&&(e=e.correspondingUseElement),e.nodeType===3?e.parentNode:e}var br=null,Wt=null,Se=null;function Ur(e){if(e=ai(e)){if(typeof br!="function")throw Error(u(280));var t=e.stateNode;t&&(t=co(t),br(e.stateNode,e.type,t))}}function Jt(e){Wt?Se?Se.push(e):Se=[e]:Wt=e}function Nt(){if(Wt){var e=Wt,t=Se;if(Se=Wt=null,Ur(e),t)for(e=0;e<t.length;e++)Ur(t[e])}}function Ri(e,t){return e(t)}function Oi(){}var $r=!1;function Ii(e,t,n){if($r)return e(t,n);$r=!0;try{return Ri(e,t,n)}finally{$r=!1,(Wt!==null||Se!==null)&&(Oi(),Nt())}}function pn(e,t){var n=e.stateNode;if(n===null)return null;var r=co(n);if(r===null)return null;n=r[t];e:switch(t){case"onClick":case"onClickCapture":case"onDoubleClick":case"onDoubleClickCapture":case"onMouseDown":case"onMouseDownCapture":case"onMouseMove":case"onMouseMoveCapture":case"onMouseUp":case"onMouseUpCapture":case"onMouseEnter":(r=!r.disabled)||(e=e.type,r=!(e==="button"||e==="input"||e==="select"||e==="textarea")),e=!r;break e;default:e=!1}if(e)return null;if(n&&typeof n!="function")throw Error(u(231,t,typeof n));return n}var sr=!1;if(N)try{var Vn={};Object.defineProperty(Vn,"passive",{get:function(){sr=!0}}),window.addEventListener("test",Vn,Vn),window.removeEventListener("test",Vn,Vn)}catch{sr=!1}function ur(e,t,n,r,i,l,s,d,p){var S=Array.prototype.slice.call(arguments,3);try{t.apply(n,S)}catch(C){this.onError(C)}}var vt=!1,Ct=null,cr=!1,Vr=null,nl={onError:function(e){vt=!0,Ct=e}};function Ai(e,t,n,r,i,l,s,d,p){vt=!1,Ct=null,ur.apply(nl,arguments)}function bi(e,t,n,r,i,l,s,d,p){if(Ai.apply(this,arguments),vt){if(vt){var S=Ct;vt=!1,Ct=null}else throw Error(u(198));cr||(cr=!0,Vr=S)}}function en(e){var t=e,n=e;if(e.alternate)for(;t.return;)t=t.return;else{e=t;do t=e,(t.flags&4098)!==0&&(n=t.return),e=t.return;while(e)}return t.tag===3?n:null}function Ui(e){if(e.tag===13){var t=e.memoizedState;if(t===null&&(e=e.alternate,e!==null&&(t=e.memoizedState)),t!==null)return t.dehydrated}return null}function $i(e){if(en(e)!==e)throw Error(u(188))}function Vi(e){var t=e.alternate;if(!t){if(t=en(e),t===null)throw Error(u(188));return t!==e?null:e}for(var n=e,r=t;;){var i=n.return;if(i===null)break;var l=i.alternate;if(l===null){if(r=i.return,r!==null){n=r;continue}break}if(i.child===l.child){for(l=i.child;l;){if(l===n)return $i(i),e;if(l===r)return $i(i),t;l=l.sibling}throw Error(u(188))}if(n.return!==r.return)n=i,r=l;else{for(var s=!1,d=i.child;d;){if(d===n){s=!0,n=i,r=l;break}if(d===r){s=!0,r=i,n=l;break}d=d.sibling}if(!s){for(d=l.child;d;){if(d===n){s=!0,n=l,r=i;break}if(d===r){s=!0,r=l,n=i;break}d=d.sibling}if(!s)throw Error(u(189))}}if(n.alternate!==r)throw Error(u(190))}if(n.tag!==3)throw Error(u(188));return n.stateNode.current===n?e:t}function Bi(e){return e=Vi(e),e!==null?Wi(e):null}function Wi(e){if(e.tag===5||e.tag===6)return e;for(e=e.child;e!==null;){var t=Wi(e);if(t!==null)return t;e=e.sibling}return null}var Hi=c.unstable_scheduleCallback,h=c.unstable_cancelCallback,D=c.unstable_shouldYield,I=c.unstable_requestPaint,O=c.unstable_now,me=c.unstable_getCurrentPriorityLevel,Re=c.unstable_ImmediatePriority,yt=c.unstable_UserBlockingPriority,Ce=c.unstable_NormalPriority,Et=c.unstable_LowPriority,tn=c.unstable_IdlePriority,Bn=null,R=null;function rt(e){if(R&&typeof R.onCommitFiberRoot=="function")try{R.onCommitFiberRoot(Bn,e,void 0,(e.current.flags&128)===128)}catch{}}var st=Math.clz32?Math.clz32:md,rl=Math.log,gd=Math.LN2;function md(e){return e>>>=0,e===0?32:31-(rl(e)/gd|0)|0}var Qi=64,Ki=4194304;function Br(e){switch(e&-e){case 1:return 1;case 2:return 2;case 4:return 4;case 8:return 8;case 16:return 16;case 32:return 32;case 64:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:return e&4194240;case 4194304:case 8388608:case 16777216:case 33554432:case 67108864:return e&130023424;case 134217728:return 134217728;case 268435456:return 268435456;case 536870912:return 536870912;case 1073741824:return 1073741824;default:return e}}function Yi(e,t){var n=e.pendingLanes;if(n===0)return 0;var r=0,i=e.suspendedLanes,l=e.pingedLanes,s=n&268435455;if(s!==0){var d=s&~i;d!==0?r=Br(d):(l&=s,l!==0&&(r=Br(l)))}else s=n&~i,s!==0?r=Br(s):l!==0&&(r=Br(l));if(r===0)return 0;if(t!==0&&t!==r&&(t&i)===0&&(i=r&-r,l=t&-t,i>=l||i===16&&(l&4194240)!==0))return t;if((r&4)!==0&&(r|=n&16),t=e.entangledLanes,t!==0)for(e=e.entanglements,t&=r;0<t;)n=31-st(t),i=1<<n,r|=e[n],t&=~i;return r}function vd(e,t){switch(e){case 1:case 2:case 4:return t+250;case 8:case 16:case 32:case 64:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:return t+5e3;case 4194304:case 8388608:case 16777216:case 33554432:case 67108864:return-1;case 134217728:case 268435456:case 536870912:case 1073741824:return-1;default:return-1}}function yd(e,t){for(var n=e.suspendedLanes,r=e.pingedLanes,i=e.expirationTimes,l=e.pendingLanes;0<l;){var s=31-st(l),d=1<<s,p=i[s];p===-1?((d&n)===0||(d&r)!==0)&&(i[s]=vd(d,t)):p<=t&&(e.expiredLanes|=d),l&=~d}}function il(e){return e=e.pendingLanes&-1073741825,e!==0?e:e&1073741824?1073741824:0}function ts(){var e=Qi;return Qi<<=1,(Qi&4194240)===0&&(Qi=64),e}function ol(e){for(var t=[],n=0;31>n;n++)t.push(e);return t}function Wr(e,t,n){e.pendingLanes|=t,t!==536870912&&(e.suspendedLanes=0,e.pingedLanes=0),e=e.eventTimes,t=31-st(t),e[t]=n}function xd(e,t){var n=e.pendingLanes&~t;e.pendingLanes=t,e.suspendedLanes=0,e.pingedLanes=0,e.expiredLanes&=t,e.mutableReadLanes&=t,e.entangledLanes&=t,t=e.entanglements;var r=e.eventTimes;for(e=e.expirationTimes;0<n;){var i=31-st(n),l=1<<i;t[i]=0,r[i]=-1,e[i]=-1,n&=~l}}function ll(e,t){var n=e.entangledLanes|=t;for(e=e.entanglements;n;){var r=31-st(n),i=1<<r;i&t|e[r]&t&&(e[r]|=t),n&=~i}}var we=0;function ns(e){return e&=-e,1<e?4<e?(e&268435455)!==0?16:536870912:4:1}var rs,al,is,os,ls,sl=!1,qi=[],hn=null,gn=null,mn=null,Hr=new Map,Qr=new Map,vn=[],wd="mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(" ");function as(e,t){switch(e){case"focusin":case"focusout":hn=null;break;case"dragenter":case"dragleave":gn=null;break;case"mouseover":case"mouseout":mn=null;break;case"pointerover":case"pointerout":Hr.delete(t.pointerId);break;case"gotpointercapture":case"lostpointercapture":Qr.delete(t.pointerId)}}function Kr(e,t,n,r,i,l){return e===null||e.nativeEvent!==l?(e={blockedOn:t,domEventName:n,eventSystemFlags:r,nativeEvent:l,targetContainers:[i]},t!==null&&(t=ai(t),t!==null&&al(t)),e):(e.eventSystemFlags|=r,t=e.targetContainers,i!==null&&t.indexOf(i)===-1&&t.push(i),e)}function kd(e,t,n,r,i){switch(t){case"focusin":return hn=Kr(hn,e,t,n,r,i),!0;case"dragenter":return gn=Kr(gn,e,t,n,r,i),!0;case"mouseover":return mn=Kr(mn,e,t,n,r,i),!0;case"pointerover":var l=i.pointerId;return Hr.set(l,Kr(Hr.get(l)||null,e,t,n,r,i)),!0;case"gotpointercapture":return l=i.pointerId,Qr.set(l,Kr(Qr.get(l)||null,e,t,n,r,i)),!0}return!1}function ss(e){var t=Wn(e.target);if(t!==null){var n=en(t);if(n!==null){if(t=n.tag,t===13){if(t=Ui(n),t!==null){e.blockedOn=t,ls(e.priority,function(){is(n)});return}}else if(t===3&&n.stateNode.current.memoizedState.isDehydrated){e.blockedOn=n.tag===3?n.stateNode.containerInfo:null;return}}}e.blockedOn=null}function Gi(e){if(e.blockedOn!==null)return!1;for(var t=e.targetContainers;0<t.length;){var n=cl(e.domEventName,e.eventSystemFlags,t[0],e.nativeEvent);if(n===null){n=e.nativeEvent;var r=new n.constructor(n.type,n);Un=r,n.target.dispatchEvent(r),Un=null}else return t=ai(n),t!==null&&al(t),e.blockedOn=n,!1;t.shift()}return!0}function us(e,t,n){Gi(e)&&n.delete(t)}function Sd(){sl=!1,hn!==null&&Gi(hn)&&(hn=null),gn!==null&&Gi(gn)&&(gn=null),mn!==null&&Gi(mn)&&(mn=null),Hr.forEach(us),Qr.forEach(us)}function Yr(e,t){e.blockedOn===t&&(e.blockedOn=null,sl||(sl=!0,c.unstable_scheduleCallback(c.unstable_NormalPriority,Sd)))}function qr(e){function t(i){return Yr(i,e)}if(0<qi.length){Yr(qi[0],e);for(var n=1;n<qi.length;n++){var r=qi[n];r.blockedOn===e&&(r.blockedOn=null)}}for(hn!==null&&Yr(hn,e),gn!==null&&Yr(gn,e),mn!==null&&Yr(mn,e),Hr.forEach(t),Qr.forEach(t),n=0;n<vn.length;n++)r=vn[n],r.blockedOn===e&&(r.blockedOn=null);for(;0<vn.length&&(n=vn[0],n.blockedOn===null);)ss(n),n.blockedOn===null&&vn.shift()}var dr=pe.ReactCurrentBatchConfig,Xi=!0;function _d(e,t,n,r){var i=we,l=dr.transition;dr.transition=null;try{we=1,ul(e,t,n,r)}finally{we=i,dr.transition=l}}function jd(e,t,n,r){var i=we,l=dr.transition;dr.transition=null;try{we=4,ul(e,t,n,r)}finally{we=i,dr.transition=l}}function ul(e,t,n,r){if(Xi){var i=cl(e,t,n,r);if(i===null)Cl(e,t,r,Zi,n),as(e,r);else if(kd(i,e,t,n,r))r.stopPropagation();else if(as(e,r),t&4&&-1<wd.indexOf(e)){for(;i!==null;){var l=ai(i);if(l!==null&&rs(l),l=cl(e,t,n,r),l===null&&Cl(e,t,r,Zi,n),l===i)break;i=l}i!==null&&r.stopPropagation()}else Cl(e,t,r,null,n)}}var Zi=null;function cl(e,t,n,r){if(Zi=null,e=$n(r),e=Wn(e),e!==null)if(t=en(e),t===null)e=null;else if(n=t.tag,n===13){if(e=Ui(t),e!==null)return e;e=null}else if(n===3){if(t.stateNode.current.memoizedState.isDehydrated)return t.tag===3?t.stateNode.containerInfo:null;e=null}else t!==e&&(e=null);return Zi=e,null}function cs(e){switch(e){case"cancel":case"click":case"close":case"contextmenu":case"copy":case"cut":case"auxclick":case"dblclick":case"dragend":case"dragstart":case"drop":case"focusin":case"focusout":case"input":case"invalid":case"keydown":case"keypress":case"keyup":case"mousedown":case"mouseup":case"paste":case"pause":case"play":case"pointercancel":case"pointerdown":case"pointerup":case"ratechange":case"reset":case"resize":case"seeked":case"submit":case"touchcancel":case"touchend":case"touchstart":case"volumechange":case"change":case"selectionchange":case"textInput":case"compositionstart":case"compositionend":case"compositionupdate":case"beforeblur":case"afterblur":case"beforeinput":case"blur":case"fullscreenchange":case"focus":case"hashchange":case"popstate":case"select":case"selectstart":return 1;case"drag":case"dragenter":case"dragexit":case"dragleave":case"dragover":case"mousemove":case"mouseout":case"mouseover":case"pointermove":case"pointerout":case"pointerover":case"scroll":case"toggle":case"touchmove":case"wheel":case"mouseenter":case"mouseleave":case"pointerenter":case"pointerleave":return 4;case"message":switch(me()){case Re:return 1;case yt:return 4;case Ce:case Et:return 16;case tn:return 536870912;default:return 16}default:return 16}}var yn=null,dl=null,Ji=null;function ds(){if(Ji)return Ji;var e,t=dl,n=t.length,r,i="value"in yn?yn.value:yn.textContent,l=i.length;for(e=0;e<n&&t[e]===i[e];e++);var s=n-e;for(r=1;r<=s&&t[n-r]===i[l-r];r++);return Ji=i.slice(e,1<r?1-r:void 0)}function eo(e){var t=e.keyCode;return"charCode"in e?(e=e.charCode,e===0&&t===13&&(e=13)):e=t,e===10&&(e=13),32<=e||e===13?e:0}function to(){return!0}function fs(){return!1}function xt(e){function t(n,r,i,l,s){this._reactName=n,this._targetInst=i,this.type=r,this.nativeEvent=l,this.target=s,this.currentTarget=null;for(var d in e)e.hasOwnProperty(d)&&(n=e[d],this[d]=n?n(l):l[d]);return this.isDefaultPrevented=(l.defaultPrevented!=null?l.defaultPrevented:l.returnValue===!1)?to:fs,this.isPropagationStopped=fs,this}return $(t.prototype,{preventDefault:function(){this.defaultPrevented=!0;var n=this.nativeEvent;n&&(n.preventDefault?n.preventDefault():typeof n.returnValue!="unknown"&&(n.returnValue=!1),this.isDefaultPrevented=to)},stopPropagation:function(){var n=this.nativeEvent;n&&(n.stopPropagation?n.stopPropagation():typeof n.cancelBubble!="unknown"&&(n.cancelBubble=!0),this.isPropagationStopped=to)},persist:function(){},isPersistent:to}),t}var fr={eventPhase:0,bubbles:0,cancelable:0,timeStamp:function(e){return e.timeStamp||Date.now()},defaultPrevented:0,isTrusted:0},fl=xt(fr),Gr=$({},fr,{view:0,detail:0}),zd=xt(Gr),pl,hl,Xr,no=$({},Gr,{screenX:0,screenY:0,clientX:0,clientY:0,pageX:0,pageY:0,ctrlKey:0,shiftKey:0,altKey:0,metaKey:0,getModifierState:ml,button:0,buttons:0,relatedTarget:function(e){return e.relatedTarget===void 0?e.fromElement===e.srcElement?e.toElement:e.fromElement:e.relatedTarget},movementX:function(e){return"movementX"in e?e.movementX:(e!==Xr&&(Xr&&e.type==="mousemove"?(pl=e.screenX-Xr.screenX,hl=e.screenY-Xr.screenY):hl=pl=0,Xr=e),pl)},movementY:function(e){return"movementY"in e?e.movementY:hl}}),ps=xt(no),Nd=$({},no,{dataTransfer:0}),Cd=xt(Nd),Ed=$({},Gr,{relatedTarget:0}),gl=xt(Ed),Dd=$({},fr,{animationName:0,elapsedTime:0,pseudoElement:0}),Ld=xt(Dd),Pd=$({},fr,{clipboardData:function(e){return"clipboardData"in e?e.clipboardData:window.clipboardData}}),Td=xt(Pd),Md=$({},fr,{data:0}),hs=xt(Md),Fd={Esc:"Escape",Spacebar:" ",Left:"ArrowLeft",Up:"ArrowUp",Right:"ArrowRight",Down:"ArrowDown",Del:"Delete",Win:"OS",Menu:"ContextMenu",Apps:"ContextMenu",Scroll:"ScrollLock",MozPrintableKey:"Unidentified"},Rd={8:"Backspace",9:"Tab",12:"Clear",13:"Enter",16:"Shift",17:"Control",18:"Alt",19:"Pause",20:"CapsLock",27:"Escape",32:" ",33:"PageUp",34:"PageDown",35:"End",36:"Home",37:"ArrowLeft",38:"ArrowUp",39:"ArrowRight",40:"ArrowDown",45:"Insert",46:"Delete",112:"F1",113:"F2",114:"F3",115:"F4",116:"F5",117:"F6",118:"F7",119:"F8",120:"F9",121:"F10",122:"F11",123:"F12",144:"NumLock",145:"ScrollLock",224:"Meta"},Od={Alt:"altKey",Control:"ctrlKey",Meta:"metaKey",Shift:"shiftKey"};function Id(e){var t=this.nativeEvent;return t.getModifierState?t.getModifierState(e):(e=Od[e])?!!t[e]:!1}function ml(){return Id}var Ad=$({},Gr,{key:function(e){if(e.key){var t=Fd[e.key]||e.key;if(t!=="Unidentified")return t}return e.type==="keypress"?(e=eo(e),e===13?"Enter":String.fromCharCode(e)):e.type==="keydown"||e.type==="keyup"?Rd[e.keyCode]||"Unidentified":""},code:0,location:0,ctrlKey:0,shiftKey:0,altKey:0,metaKey:0,repeat:0,locale:0,getModifierState:ml,charCode:function(e){return e.type==="keypress"?eo(e):0},keyCode:function(e){return e.type==="keydown"||e.type==="keyup"?e.keyCode:0},which:function(e){return e.type==="keypress"?eo(e):e.type==="keydown"||e.type==="keyup"?e.keyCode:0}}),bd=xt(Ad),Ud=$({},no,{pointerId:0,width:0,height:0,pressure:0,tangentialPressure:0,tiltX:0,tiltY:0,twist:0,pointerType:0,isPrimary:0}),gs=xt(Ud),$d=$({},Gr,{touches:0,targetTouches:0,changedTouches:0,altKey:0,metaKey:0,ctrlKey:0,shiftKey:0,getModifierState:ml}),Vd=xt($d),Bd=$({},fr,{propertyName:0,elapsedTime:0,pseudoElement:0}),Wd=xt(Bd),Hd=$({},no,{deltaX:function(e){return"deltaX"in e?e.deltaX:"wheelDeltaX"in e?-e.wheelDeltaX:0},deltaY:function(e){return"deltaY"in e?e.deltaY:"wheelDeltaY"in e?-e.wheelDeltaY:"wheelDelta"in e?-e.wheelDelta:0},deltaZ:0,deltaMode:0}),Qd=xt(Hd),Kd=[9,13,27,32],vl=N&&"CompositionEvent"in window,Zr=null;N&&"documentMode"in document&&(Zr=document.documentMode);var Yd=N&&"TextEvent"in window&&!Zr,ms=N&&(!vl||Zr&&8<Zr&&11>=Zr),vs=" ",ys=!1;function xs(e,t){switch(e){case"keyup":return Kd.indexOf(t.keyCode)!==-1;case"keydown":return t.keyCode!==229;case"keypress":case"mousedown":case"focusout":return!0;default:return!1}}function ws(e){return e=e.detail,typeof e=="object"&&"data"in e?e.data:null}var pr=!1;function qd(e,t){switch(e){case"compositionend":return ws(t);case"keypress":return t.which!==32?null:(ys=!0,vs);case"textInput":return e=t.data,e===vs&&ys?null:e;default:return null}}function Gd(e,t){if(pr)return e==="compositionend"||!vl&&xs(e,t)?(e=ds(),Ji=dl=yn=null,pr=!1,e):null;switch(e){case"paste":return null;case"keypress":if(!(t.ctrlKey||t.altKey||t.metaKey)||t.ctrlKey&&t.altKey){if(t.char&&1<t.char.length)return t.char;if(t.which)return String.fromCharCode(t.which)}return null;case"compositionend":return ms&&t.locale!=="ko"?null:t.data;default:return null}}var Xd={color:!0,date:!0,datetime:!0,"datetime-local":!0,email:!0,month:!0,number:!0,password:!0,range:!0,search:!0,tel:!0,text:!0,time:!0,url:!0,week:!0};function ks(e){var t=e&&e.nodeName&&e.nodeName.toLowerCase();return t==="input"?!!Xd[e.type]:t==="textarea"}function Ss(e,t,n,r){Jt(r),t=ao(t,"onChange"),0<t.length&&(n=new fl("onChange","change",null,n,r),e.push({event:n,listeners:t}))}var Jr=null,ei=null;function Zd(e){Us(e,0)}function ro(e){var t=yr(e);if(On(t))return e}function Jd(e,t){if(e==="change")return t}var _s=!1;if(N){var yl;if(N){var xl="oninput"in document;if(!xl){var js=document.createElement("div");js.setAttribute("oninput","return;"),xl=typeof js.oninput=="function"}yl=xl}else yl=!1;_s=yl&&(!document.documentMode||9<document.documentMode)}function zs(){Jr&&(Jr.detachEvent("onpropertychange",Ns),ei=Jr=null)}function Ns(e){if(e.propertyName==="value"&&ro(ei)){var t=[];Ss(t,ei,e,$n(e)),Ii(Zd,t)}}function ef(e,t,n){e==="focusin"?(zs(),Jr=t,ei=n,Jr.attachEvent("onpropertychange",Ns)):e==="focusout"&&zs()}function tf(e){if(e==="selectionchange"||e==="keyup"||e==="keydown")return ro(ei)}function nf(e,t){if(e==="click")return ro(t)}function rf(e,t){if(e==="input"||e==="change")return ro(t)}function of(e,t){return e===t&&(e!==0||1/e===1/t)||e!==e&&t!==t}var At=typeof Object.is=="function"?Object.is:of;function ti(e,t){if(At(e,t))return!0;if(typeof e!="object"||e===null||typeof t!="object"||t===null)return!1;var n=Object.keys(e),r=Object.keys(t);if(n.length!==r.length)return!1;for(r=0;r<n.length;r++){var i=n[r];if(!F.call(t,i)||!At(e[i],t[i]))return!1}return!0}function Cs(e){for(;e&&e.firstChild;)e=e.firstChild;return e}function Es(e,t){var n=Cs(e);e=0;for(var r;n;){if(n.nodeType===3){if(r=e+n.textContent.length,e<=t&&r>=t)return{node:n,offset:t-e};e=r}e:{for(;n;){if(n.nextSibling){n=n.nextSibling;break e}n=n.parentNode}n=void 0}n=Cs(n)}}function Ds(e,t){return e&&t?e===t?!0:e&&e.nodeType===3?!1:t&&t.nodeType===3?Ds(e,t.parentNode):"contains"in e?e.contains(t):e.compareDocumentPosition?!!(e.compareDocumentPosition(t)&16):!1:!1}function Ls(){for(var e=window,t=$e();t instanceof e.HTMLIFrameElement;){try{var n=typeof t.contentWindow.location.href=="string"}catch{n=!1}if(n)e=t.contentWindow;else break;t=$e(e.document)}return t}function wl(e){var t=e&&e.nodeName&&e.nodeName.toLowerCase();return t&&(t==="input"&&(e.type==="text"||e.type==="search"||e.type==="tel"||e.type==="url"||e.type==="password")||t==="textarea"||e.contentEditable==="true")}function lf(e){var t=Ls(),n=e.focusedElem,r=e.selectionRange;if(t!==n&&n&&n.ownerDocument&&Ds(n.ownerDocument.documentElement,n)){if(r!==null&&wl(n)){if(t=r.start,e=r.end,e===void 0&&(e=t),"selectionStart"in n)n.selectionStart=t,n.selectionEnd=Math.min(e,n.value.length);else if(e=(t=n.ownerDocument||document)&&t.defaultView||window,e.getSelection){e=e.getSelection();var i=n.textContent.length,l=Math.min(r.start,i);r=r.end===void 0?l:Math.min(r.end,i),!e.extend&&l>r&&(i=r,r=l,l=i),i=Es(n,l);var s=Es(n,r);i&&s&&(e.rangeCount!==1||e.anchorNode!==i.node||e.anchorOffset!==i.offset||e.focusNode!==s.node||e.focusOffset!==s.offset)&&(t=t.createRange(),t.setStart(i.node,i.offset),e.removeAllRanges(),l>r?(e.addRange(t),e.extend(s.node,s.offset)):(t.setEnd(s.node,s.offset),e.addRange(t)))}}for(t=[],e=n;e=e.parentNode;)e.nodeType===1&&t.push({element:e,left:e.scrollLeft,top:e.scrollTop});for(typeof n.focus=="function"&&n.focus(),n=0;n<t.length;n++)e=t[n],e.element.scrollLeft=e.left,e.element.scrollTop=e.top}}var af=N&&"documentMode"in document&&11>=document.documentMode,hr=null,kl=null,ni=null,Sl=!1;function Ps(e,t,n){var r=n.window===n?n.document:n.nodeType===9?n:n.ownerDocument;Sl||hr==null||hr!==$e(r)||(r=hr,"selectionStart"in r&&wl(r)?r={start:r.selectionStart,end:r.selectionEnd}:(r=(r.ownerDocument&&r.ownerDocument.defaultView||window).getSelection(),r={anchorNode:r.anchorNode,anchorOffset:r.anchorOffset,focusNode:r.focusNode,focusOffset:r.focusOffset}),ni&&ti(ni,r)||(ni=r,r=ao(kl,"onSelect"),0<r.length&&(t=new fl("onSelect","select",null,t,n),e.push({event:t,listeners:r}),t.target=hr)))}function io(e,t){var n={};return n[e.toLowerCase()]=t.toLowerCase(),n["Webkit"+e]="webkit"+t,n["Moz"+e]="moz"+t,n}var gr={animationend:io("Animation","AnimationEnd"),animationiteration:io("Animation","AnimationIteration"),animationstart:io("Animation","AnimationStart"),transitionend:io("Transition","TransitionEnd")},_l={},Ts={};N&&(Ts=document.createElement("div").style,"AnimationEvent"in window||(delete gr.animationend.animation,delete gr.animationiteration.animation,delete gr.animationstart.animation),"TransitionEvent"in window||delete gr.transitionend.transition);function oo(e){if(_l[e])return _l[e];if(!gr[e])return e;var t=gr[e],n;for(n in t)if(t.hasOwnProperty(n)&&n in Ts)return _l[e]=t[n];return e}var Ms=oo("animationend"),Fs=oo("animationiteration"),Rs=oo("animationstart"),Os=oo("transitionend"),Is=new Map,As="abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(" ");function xn(e,t){Is.set(e,t),x(t,[e])}for(var jl=0;jl<As.length;jl++){var zl=As[jl],sf=zl.toLowerCase(),uf=zl[0].toUpperCase()+zl.slice(1);xn(sf,"on"+uf)}xn(Ms,"onAnimationEnd"),xn(Fs,"onAnimationIteration"),xn(Rs,"onAnimationStart"),xn("dblclick","onDoubleClick"),xn("focusin","onFocus"),xn("focusout","onBlur"),xn(Os,"onTransitionEnd"),k("onMouseEnter",["mouseout","mouseover"]),k("onMouseLeave",["mouseout","mouseover"]),k("onPointerEnter",["pointerout","pointerover"]),k("onPointerLeave",["pointerout","pointerover"]),x("onChange","change click focusin focusout input keydown keyup selectionchange".split(" ")),x("onSelect","focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" ")),x("onBeforeInput",["compositionend","keypress","textInput","paste"]),x("onCompositionEnd","compositionend focusout keydown keypress keyup mousedown".split(" ")),x("onCompositionStart","compositionstart focusout keydown keypress keyup mousedown".split(" ")),x("onCompositionUpdate","compositionupdate focusout keydown keypress keyup mousedown".split(" "));var ri="abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(" "),cf=new Set("cancel close invalid load scroll toggle".split(" ").concat(ri));function bs(e,t,n){var r=e.type||"unknown-event";e.currentTarget=n,bi(r,t,void 0,e),e.currentTarget=null}function Us(e,t){t=(t&4)!==0;for(var n=0;n<e.length;n++){var r=e[n],i=r.event;r=r.listeners;e:{var l=void 0;if(t)for(var s=r.length-1;0<=s;s--){var d=r[s],p=d.instance,S=d.currentTarget;if(d=d.listener,p!==l&&i.isPropagationStopped())break e;bs(i,d,S),l=p}else for(s=0;s<r.length;s++){if(d=r[s],p=d.instance,S=d.currentTarget,d=d.listener,p!==l&&i.isPropagationStopped())break e;bs(i,d,S),l=p}}}if(cr)throw e=Vr,cr=!1,Vr=null,e}function Ee(e,t){var n=t[Ml];n===void 0&&(n=t[Ml]=new Set);var r=e+"__bubble";n.has(r)||($s(t,e,2,!1),n.add(r))}function Nl(e,t,n){var r=0;t&&(r|=4),$s(n,e,r,t)}var lo="_reactListening"+Math.random().toString(36).slice(2);function ii(e){if(!e[lo]){e[lo]=!0,f.forEach(function(n){n!=="selectionchange"&&(cf.has(n)||Nl(n,!1,e),Nl(n,!0,e))});var t=e.nodeType===9?e:e.ownerDocument;t===null||t[lo]||(t[lo]=!0,Nl("selectionchange",!1,t))}}function $s(e,t,n,r){switch(cs(t)){case 1:var i=_d;break;case 4:i=jd;break;default:i=ul}n=i.bind(null,t,n,e),i=void 0,!sr||t!=="touchstart"&&t!=="touchmove"&&t!=="wheel"||(i=!0),r?i!==void 0?e.addEventListener(t,n,{capture:!0,passive:i}):e.addEventListener(t,n,!0):i!==void 0?e.addEventListener(t,n,{passive:i}):e.addEventListener(t,n,!1)}function Cl(e,t,n,r,i){var l=r;if((t&1)===0&&(t&2)===0&&r!==null)e:for(;;){if(r===null)return;var s=r.tag;if(s===3||s===4){var d=r.stateNode.containerInfo;if(d===i||d.nodeType===8&&d.parentNode===i)break;if(s===4)for(s=r.return;s!==null;){var p=s.tag;if((p===3||p===4)&&(p=s.stateNode.containerInfo,p===i||p.nodeType===8&&p.parentNode===i))return;s=s.return}for(;d!==null;){if(s=Wn(d),s===null)return;if(p=s.tag,p===5||p===6){r=l=s;continue e}d=d.parentNode}}r=r.return}Ii(function(){var S=l,C=$n(n),L=[];e:{var z=Is.get(e);if(z!==void 0){var b=fl,W=e;switch(e){case"keypress":if(eo(n)===0)break e;case"keydown":case"keyup":b=bd;break;case"focusin":W="focus",b=gl;break;case"focusout":W="blur",b=gl;break;case"beforeblur":case"afterblur":b=gl;break;case"click":if(n.button===2)break e;case"auxclick":case"dblclick":case"mousedown":case"mousemove":case"mouseup":case"mouseout":case"mouseover":case"contextmenu":b=ps;break;case"drag":case"dragend":case"dragenter":case"dragexit":case"dragleave":case"dragover":case"dragstart":case"drop":b=Cd;break;case"touchcancel":case"touchend":case"touchmove":case"touchstart":b=Vd;break;case Ms:case Fs:case Rs:b=Ld;break;case Os:b=Wd;break;case"scroll":b=zd;break;case"wheel":b=Qd;break;case"copy":case"cut":case"paste":b=Td;break;case"gotpointercapture":case"lostpointercapture":case"pointercancel":case"pointerdown":case"pointermove":case"pointerout":case"pointerover":case"pointerup":b=gs}var Q=(t&4)!==0,Oe=!Q&&e==="scroll",y=Q?z!==null?z+"Capture":null:z;Q=[];for(var m=S,w;m!==null;){w=m;var P=w.stateNode;if(w.tag===5&&P!==null&&(w=P,y!==null&&(P=pn(m,y),P!=null&&Q.push(oi(m,P,w)))),Oe)break;m=m.return}0<Q.length&&(z=new b(z,W,null,n,C),L.push({event:z,listeners:Q}))}}if((t&7)===0){e:{if(z=e==="mouseover"||e==="pointerover",b=e==="mouseout"||e==="pointerout",z&&n!==Un&&(W=n.relatedTarget||n.fromElement)&&(Wn(W)||W[nn]))break e;if((b||z)&&(z=C.window===C?C:(z=C.ownerDocument)?z.defaultView||z.parentWindow:window,b?(W=n.relatedTarget||n.toElement,b=S,W=W?Wn(W):null,W!==null&&(Oe=en(W),W!==Oe||W.tag!==5&&W.tag!==6)&&(W=null)):(b=null,W=S),b!==W)){if(Q=ps,P="onMouseLeave",y="onMouseEnter",m="mouse",(e==="pointerout"||e==="pointerover")&&(Q=gs,P="onPointerLeave",y="onPointerEnter",m="pointer"),Oe=b==null?z:yr(b),w=W==null?z:yr(W),z=new Q(P,m+"leave",b,n,C),z.target=Oe,z.relatedTarget=w,P=null,Wn(C)===S&&(Q=new Q(y,m+"enter",W,n,C),Q.target=w,Q.relatedTarget=Oe,P=Q),Oe=P,b&&W)t:{for(Q=b,y=W,m=0,w=Q;w;w=mr(w))m++;for(w=0,P=y;P;P=mr(P))w++;for(;0<m-w;)Q=mr(Q),m--;for(;0<w-m;)y=mr(y),w--;for(;m--;){if(Q===y||y!==null&&Q===y.alternate)break t;Q=mr(Q),y=mr(y)}Q=null}else Q=null;b!==null&&Vs(L,z,b,Q,!1),W!==null&&Oe!==null&&Vs(L,Oe,W,Q,!0)}}e:{if(z=S?yr(S):window,b=z.nodeName&&z.nodeName.toLowerCase(),b==="select"||b==="input"&&z.type==="file")var Y=Jd;else if(ks(z))if(_s)Y=rf;else{Y=tf;var J=ef}else(b=z.nodeName)&&b.toLowerCase()==="input"&&(z.type==="checkbox"||z.type==="radio")&&(Y=nf);if(Y&&(Y=Y(e,S))){Ss(L,Y,n,C);break e}J&&J(e,z,S),e==="focusout"&&(J=z._wrapperState)&&J.controlled&&z.type==="number"&&zt(z,"number",z.value)}switch(J=S?yr(S):window,e){case"focusin":(ks(J)||J.contentEditable==="true")&&(hr=J,kl=S,ni=null);break;case"focusout":ni=kl=hr=null;break;case"mousedown":Sl=!0;break;case"contextmenu":case"mouseup":case"dragend":Sl=!1,Ps(L,n,C);break;case"selectionchange":if(af)break;case"keydown":case"keyup":Ps(L,n,C)}var ee;if(vl)e:{switch(e){case"compositionstart":var re="onCompositionStart";break e;case"compositionend":re="onCompositionEnd";break e;case"compositionupdate":re="onCompositionUpdate";break e}re=void 0}else pr?xs(e,n)&&(re="onCompositionEnd"):e==="keydown"&&n.keyCode===229&&(re="onCompositionStart");re&&(ms&&n.locale!=="ko"&&(pr||re!=="onCompositionStart"?re==="onCompositionEnd"&&pr&&(ee=ds()):(yn=C,dl="value"in yn?yn.value:yn.textContent,pr=!0)),J=ao(S,re),0<J.length&&(re=new hs(re,e,null,n,C),L.push({event:re,listeners:J}),ee?re.data=ee:(ee=ws(n),ee!==null&&(re.data=ee)))),(ee=Yd?qd(e,n):Gd(e,n))&&(S=ao(S,"onBeforeInput"),0<S.length&&(C=new hs("onBeforeInput","beforeinput",null,n,C),L.push({event:C,listeners:S}),C.data=ee))}Us(L,t)})}function oi(e,t,n){return{instance:e,listener:t,currentTarget:n}}function ao(e,t){for(var n=t+"Capture",r=[];e!==null;){var i=e,l=i.stateNode;i.tag===5&&l!==null&&(i=l,l=pn(e,n),l!=null&&r.unshift(oi(e,l,i)),l=pn(e,t),l!=null&&r.push(oi(e,l,i))),e=e.return}return r}function mr(e){if(e===null)return null;do e=e.return;while(e&&e.tag!==5);return e||null}function Vs(e,t,n,r,i){for(var l=t._reactName,s=[];n!==null&&n!==r;){var d=n,p=d.alternate,S=d.stateNode;if(p!==null&&p===r)break;d.tag===5&&S!==null&&(d=S,i?(p=pn(n,l),p!=null&&s.unshift(oi(n,p,d))):i||(p=pn(n,l),p!=null&&s.push(oi(n,p,d)))),n=n.return}s.length!==0&&e.push({event:t,listeners:s})}var df=/\r\n?/g,ff=/\u0000|\uFFFD/g;function Bs(e){return(typeof e=="string"?e:""+e).replace(df,`
`).replace(ff,"")}function so(e,t,n){if(t=Bs(t),Bs(e)!==t&&n)throw Error(u(425))}function uo(){}var El=null,Dl=null;function Ll(e,t){return e==="textarea"||e==="noscript"||typeof t.children=="string"||typeof t.children=="number"||typeof t.dangerouslySetInnerHTML=="object"&&t.dangerouslySetInnerHTML!==null&&t.dangerouslySetInnerHTML.__html!=null}var Pl=typeof setTimeout=="function"?setTimeout:void 0,pf=typeof clearTimeout=="function"?clearTimeout:void 0,Ws=typeof Promise=="function"?Promise:void 0,hf=typeof queueMicrotask=="function"?queueMicrotask:typeof Ws<"u"?function(e){return Ws.resolve(null).then(e).catch(gf)}:Pl;function gf(e){setTimeout(function(){throw e})}function Tl(e,t){var n=t,r=0;do{var i=n.nextSibling;if(e.removeChild(n),i&&i.nodeType===8)if(n=i.data,n==="/$"){if(r===0){e.removeChild(i),qr(t);return}r--}else n!=="$"&&n!=="$?"&&n!=="$!"||r++;n=i}while(n);qr(t)}function wn(e){for(;e!=null;e=e.nextSibling){var t=e.nodeType;if(t===1||t===3)break;if(t===8){if(t=e.data,t==="$"||t==="$!"||t==="$?")break;if(t==="/$")return null}}return e}function Hs(e){e=e.previousSibling;for(var t=0;e;){if(e.nodeType===8){var n=e.data;if(n==="$"||n==="$!"||n==="$?"){if(t===0)return e;t--}else n==="/$"&&t++}e=e.previousSibling}return null}var vr=Math.random().toString(36).slice(2),Ht="__reactFiber$"+vr,li="__reactProps$"+vr,nn="__reactContainer$"+vr,Ml="__reactEvents$"+vr,mf="__reactListeners$"+vr,vf="__reactHandles$"+vr;function Wn(e){var t=e[Ht];if(t)return t;for(var n=e.parentNode;n;){if(t=n[nn]||n[Ht]){if(n=t.alternate,t.child!==null||n!==null&&n.child!==null)for(e=Hs(e);e!==null;){if(n=e[Ht])return n;e=Hs(e)}return t}e=n,n=e.parentNode}return null}function ai(e){return e=e[Ht]||e[nn],!e||e.tag!==5&&e.tag!==6&&e.tag!==13&&e.tag!==3?null:e}function yr(e){if(e.tag===5||e.tag===6)return e.stateNode;throw Error(u(33))}function co(e){return e[li]||null}var Fl=[],xr=-1;function kn(e){return{current:e}}function De(e){0>xr||(e.current=Fl[xr],Fl[xr]=null,xr--)}function Ne(e,t){xr++,Fl[xr]=e.current,e.current=t}var Sn={},Ze=kn(Sn),ut=kn(!1),Hn=Sn;function wr(e,t){var n=e.type.contextTypes;if(!n)return Sn;var r=e.stateNode;if(r&&r.__reactInternalMemoizedUnmaskedChildContext===t)return r.__reactInternalMemoizedMaskedChildContext;var i={},l;for(l in n)i[l]=t[l];return r&&(e=e.stateNode,e.__reactInternalMemoizedUnmaskedChildContext=t,e.__reactInternalMemoizedMaskedChildContext=i),i}function ct(e){return e=e.childContextTypes,e!=null}function fo(){De(ut),De(Ze)}function Qs(e,t,n){if(Ze.current!==Sn)throw Error(u(168));Ne(Ze,t),Ne(ut,n)}function Ks(e,t,n){var r=e.stateNode;if(t=t.childContextTypes,typeof r.getChildContext!="function")return n;r=r.getChildContext();for(var i in r)if(!(i in t))throw Error(u(108,xe(e)||"Unknown",i));return $({},n,r)}function po(e){return e=(e=e.stateNode)&&e.__reactInternalMemoizedMergedChildContext||Sn,Hn=Ze.current,Ne(Ze,e),Ne(ut,ut.current),!0}function Ys(e,t,n){var r=e.stateNode;if(!r)throw Error(u(169));n?(e=Ks(e,t,Hn),r.__reactInternalMemoizedMergedChildContext=e,De(ut),De(Ze),Ne(Ze,e)):De(ut),Ne(ut,n)}var rn=null,ho=!1,Rl=!1;function qs(e){rn===null?rn=[e]:rn.push(e)}function yf(e){ho=!0,qs(e)}function _n(){if(!Rl&&rn!==null){Rl=!0;var e=0,t=we;try{var n=rn;for(we=1;e<n.length;e++){var r=n[e];do r=r(!0);while(r!==null)}rn=null,ho=!1}catch(i){throw rn!==null&&(rn=rn.slice(e+1)),Hi(Re,_n),i}finally{we=t,Rl=!1}}return null}var kr=[],Sr=0,go=null,mo=0,Dt=[],Lt=0,Qn=null,on=1,ln="";function Kn(e,t){kr[Sr++]=mo,kr[Sr++]=go,go=e,mo=t}function Gs(e,t,n){Dt[Lt++]=on,Dt[Lt++]=ln,Dt[Lt++]=Qn,Qn=e;var r=on;e=ln;var i=32-st(r)-1;r&=~(1<<i),n+=1;var l=32-st(t)+i;if(30<l){var s=i-i%5;l=(r&(1<<s)-1).toString(32),r>>=s,i-=s,on=1<<32-st(t)+i|n<<i|r,ln=l+e}else on=1<<l|n<<i|r,ln=e}function Ol(e){e.return!==null&&(Kn(e,1),Gs(e,1,0))}function Il(e){for(;e===go;)go=kr[--Sr],kr[Sr]=null,mo=kr[--Sr],kr[Sr]=null;for(;e===Qn;)Qn=Dt[--Lt],Dt[Lt]=null,ln=Dt[--Lt],Dt[Lt]=null,on=Dt[--Lt],Dt[Lt]=null}var wt=null,kt=null,Le=!1,bt=null;function Xs(e,t){var n=Ft(5,null,null,0);n.elementType="DELETED",n.stateNode=t,n.return=e,t=e.deletions,t===null?(e.deletions=[n],e.flags|=16):t.push(n)}function Zs(e,t){switch(e.tag){case 5:var n=e.type;return t=t.nodeType!==1||n.toLowerCase()!==t.nodeName.toLowerCase()?null:t,t!==null?(e.stateNode=t,wt=e,kt=wn(t.firstChild),!0):!1;case 6:return t=e.pendingProps===""||t.nodeType!==3?null:t,t!==null?(e.stateNode=t,wt=e,kt=null,!0):!1;case 13:return t=t.nodeType!==8?null:t,t!==null?(n=Qn!==null?{id:on,overflow:ln}:null,e.memoizedState={dehydrated:t,treeContext:n,retryLane:1073741824},n=Ft(18,null,null,0),n.stateNode=t,n.return=e,e.child=n,wt=e,kt=null,!0):!1;default:return!1}}function Al(e){return(e.mode&1)!==0&&(e.flags&128)===0}function bl(e){if(Le){var t=kt;if(t){var n=t;if(!Zs(e,t)){if(Al(e))throw Error(u(418));t=wn(n.nextSibling);var r=wt;t&&Zs(e,t)?Xs(r,n):(e.flags=e.flags&-4097|2,Le=!1,wt=e)}}else{if(Al(e))throw Error(u(418));e.flags=e.flags&-4097|2,Le=!1,wt=e}}}function Js(e){for(e=e.return;e!==null&&e.tag!==5&&e.tag!==3&&e.tag!==13;)e=e.return;wt=e}function vo(e){if(e!==wt)return!1;if(!Le)return Js(e),Le=!0,!1;var t;if((t=e.tag!==3)&&!(t=e.tag!==5)&&(t=e.type,t=t!=="head"&&t!=="body"&&!Ll(e.type,e.memoizedProps)),t&&(t=kt)){if(Al(e))throw eu(),Error(u(418));for(;t;)Xs(e,t),t=wn(t.nextSibling)}if(Js(e),e.tag===13){if(e=e.memoizedState,e=e!==null?e.dehydrated:null,!e)throw Error(u(317));e:{for(e=e.nextSibling,t=0;e;){if(e.nodeType===8){var n=e.data;if(n==="/$"){if(t===0){kt=wn(e.nextSibling);break e}t--}else n!=="$"&&n!=="$!"&&n!=="$?"||t++}e=e.nextSibling}kt=null}}else kt=wt?wn(e.stateNode.nextSibling):null;return!0}function eu(){for(var e=kt;e;)e=wn(e.nextSibling)}function _r(){kt=wt=null,Le=!1}function Ul(e){bt===null?bt=[e]:bt.push(e)}var xf=pe.ReactCurrentBatchConfig;function si(e,t,n){if(e=n.ref,e!==null&&typeof e!="function"&&typeof e!="object"){if(n._owner){if(n=n._owner,n){if(n.tag!==1)throw Error(u(309));var r=n.stateNode}if(!r)throw Error(u(147,e));var i=r,l=""+e;return t!==null&&t.ref!==null&&typeof t.ref=="function"&&t.ref._stringRef===l?t.ref:(t=function(s){var d=i.refs;s===null?delete d[l]:d[l]=s},t._stringRef=l,t)}if(typeof e!="string")throw Error(u(284));if(!n._owner)throw Error(u(290,e))}return e}function yo(e,t){throw e=Object.prototype.toString.call(t),Error(u(31,e==="[object Object]"?"object with keys {"+Object.keys(t).join(", ")+"}":e))}function tu(e){var t=e._init;return t(e._payload)}function nu(e){function t(y,m){if(e){var w=y.deletions;w===null?(y.deletions=[m],y.flags|=16):w.push(m)}}function n(y,m){if(!e)return null;for(;m!==null;)t(y,m),m=m.sibling;return null}function r(y,m){for(y=new Map;m!==null;)m.key!==null?y.set(m.key,m):y.set(m.index,m),m=m.sibling;return y}function i(y,m){return y=Pn(y,m),y.index=0,y.sibling=null,y}function l(y,m,w){return y.index=w,e?(w=y.alternate,w!==null?(w=w.index,w<m?(y.flags|=2,m):w):(y.flags|=2,m)):(y.flags|=1048576,m)}function s(y){return e&&y.alternate===null&&(y.flags|=2),y}function d(y,m,w,P){return m===null||m.tag!==6?(m=Pa(w,y.mode,P),m.return=y,m):(m=i(m,w),m.return=y,m)}function p(y,m,w,P){var Y=w.type;return Y===_e?C(y,m,w.props.children,P,w.key):m!==null&&(m.elementType===Y||typeof Y=="object"&&Y!==null&&Y.$$typeof===ye&&tu(Y)===m.type)?(P=i(m,w.props),P.ref=si(y,m,w),P.return=y,P):(P=Vo(w.type,w.key,w.props,null,y.mode,P),P.ref=si(y,m,w),P.return=y,P)}function S(y,m,w,P){return m===null||m.tag!==4||m.stateNode.containerInfo!==w.containerInfo||m.stateNode.implementation!==w.implementation?(m=Ta(w,y.mode,P),m.return=y,m):(m=i(m,w.children||[]),m.return=y,m)}function C(y,m,w,P,Y){return m===null||m.tag!==7?(m=tr(w,y.mode,P,Y),m.return=y,m):(m=i(m,w),m.return=y,m)}function L(y,m,w){if(typeof m=="string"&&m!==""||typeof m=="number")return m=Pa(""+m,y.mode,w),m.return=y,m;if(typeof m=="object"&&m!==null){switch(m.$$typeof){case Me:return w=Vo(m.type,m.key,m.props,null,y.mode,w),w.ref=si(y,null,m),w.return=y,w;case he:return m=Ta(m,y.mode,w),m.return=y,m;case ye:var P=m._init;return L(y,P(m._payload),w)}if(It(m)||A(m))return m=tr(m,y.mode,w,null),m.return=y,m;yo(y,m)}return null}function z(y,m,w,P){var Y=m!==null?m.key:null;if(typeof w=="string"&&w!==""||typeof w=="number")return Y!==null?null:d(y,m,""+w,P);if(typeof w=="object"&&w!==null){switch(w.$$typeof){case Me:return w.key===Y?p(y,m,w,P):null;case he:return w.key===Y?S(y,m,w,P):null;case ye:return Y=w._init,z(y,m,Y(w._payload),P)}if(It(w)||A(w))return Y!==null?null:C(y,m,w,P,null);yo(y,w)}return null}function b(y,m,w,P,Y){if(typeof P=="string"&&P!==""||typeof P=="number")return y=y.get(w)||null,d(m,y,""+P,Y);if(typeof P=="object"&&P!==null){switch(P.$$typeof){case Me:return y=y.get(P.key===null?w:P.key)||null,p(m,y,P,Y);case he:return y=y.get(P.key===null?w:P.key)||null,S(m,y,P,Y);case ye:var J=P._init;return b(y,m,w,J(P._payload),Y)}if(It(P)||A(P))return y=y.get(w)||null,C(m,y,P,Y,null);yo(m,P)}return null}function W(y,m,w,P){for(var Y=null,J=null,ee=m,re=m=0,We=null;ee!==null&&re<w.length;re++){ee.index>re?(We=ee,ee=null):We=ee.sibling;var ve=z(y,ee,w[re],P);if(ve===null){ee===null&&(ee=We);break}e&&ee&&ve.alternate===null&&t(y,ee),m=l(ve,m,re),J===null?Y=ve:J.sibling=ve,J=ve,ee=We}if(re===w.length)return n(y,ee),Le&&Kn(y,re),Y;if(ee===null){for(;re<w.length;re++)ee=L(y,w[re],P),ee!==null&&(m=l(ee,m,re),J===null?Y=ee:J.sibling=ee,J=ee);return Le&&Kn(y,re),Y}for(ee=r(y,ee);re<w.length;re++)We=b(ee,y,re,w[re],P),We!==null&&(e&&We.alternate!==null&&ee.delete(We.key===null?re:We.key),m=l(We,m,re),J===null?Y=We:J.sibling=We,J=We);return e&&ee.forEach(function(Tn){return t(y,Tn)}),Le&&Kn(y,re),Y}function Q(y,m,w,P){var Y=A(w);if(typeof Y!="function")throw Error(u(150));if(w=Y.call(w),w==null)throw Error(u(151));for(var J=Y=null,ee=m,re=m=0,We=null,ve=w.next();ee!==null&&!ve.done;re++,ve=w.next()){ee.index>re?(We=ee,ee=null):We=ee.sibling;var Tn=z(y,ee,ve.value,P);if(Tn===null){ee===null&&(ee=We);break}e&&ee&&Tn.alternate===null&&t(y,ee),m=l(Tn,m,re),J===null?Y=Tn:J.sibling=Tn,J=Tn,ee=We}if(ve.done)return n(y,ee),Le&&Kn(y,re),Y;if(ee===null){for(;!ve.done;re++,ve=w.next())ve=L(y,ve.value,P),ve!==null&&(m=l(ve,m,re),J===null?Y=ve:J.sibling=ve,J=ve);return Le&&Kn(y,re),Y}for(ee=r(y,ee);!ve.done;re++,ve=w.next())ve=b(ee,y,re,ve.value,P),ve!==null&&(e&&ve.alternate!==null&&ee.delete(ve.key===null?re:ve.key),m=l(ve,m,re),J===null?Y=ve:J.sibling=ve,J=ve);return e&&ee.forEach(function(Zf){return t(y,Zf)}),Le&&Kn(y,re),Y}function Oe(y,m,w,P){if(typeof w=="object"&&w!==null&&w.type===_e&&w.key===null&&(w=w.props.children),typeof w=="object"&&w!==null){switch(w.$$typeof){case Me:e:{for(var Y=w.key,J=m;J!==null;){if(J.key===Y){if(Y=w.type,Y===_e){if(J.tag===7){n(y,J.sibling),m=i(J,w.props.children),m.return=y,y=m;break e}}else if(J.elementType===Y||typeof Y=="object"&&Y!==null&&Y.$$typeof===ye&&tu(Y)===J.type){n(y,J.sibling),m=i(J,w.props),m.ref=si(y,J,w),m.return=y,y=m;break e}n(y,J);break}else t(y,J);J=J.sibling}w.type===_e?(m=tr(w.props.children,y.mode,P,w.key),m.return=y,y=m):(P=Vo(w.type,w.key,w.props,null,y.mode,P),P.ref=si(y,m,w),P.return=y,y=P)}return s(y);case he:e:{for(J=w.key;m!==null;){if(m.key===J)if(m.tag===4&&m.stateNode.containerInfo===w.containerInfo&&m.stateNode.implementation===w.implementation){n(y,m.sibling),m=i(m,w.children||[]),m.return=y,y=m;break e}else{n(y,m);break}else t(y,m);m=m.sibling}m=Ta(w,y.mode,P),m.return=y,y=m}return s(y);case ye:return J=w._init,Oe(y,m,J(w._payload),P)}if(It(w))return W(y,m,w,P);if(A(w))return Q(y,m,w,P);yo(y,w)}return typeof w=="string"&&w!==""||typeof w=="number"?(w=""+w,m!==null&&m.tag===6?(n(y,m.sibling),m=i(m,w),m.return=y,y=m):(n(y,m),m=Pa(w,y.mode,P),m.return=y,y=m),s(y)):n(y,m)}return Oe}var jr=nu(!0),ru=nu(!1),xo=kn(null),wo=null,zr=null,$l=null;function Vl(){$l=zr=wo=null}function Bl(e){var t=xo.current;De(xo),e._currentValue=t}function Wl(e,t,n){for(;e!==null;){var r=e.alternate;if((e.childLanes&t)!==t?(e.childLanes|=t,r!==null&&(r.childLanes|=t)):r!==null&&(r.childLanes&t)!==t&&(r.childLanes|=t),e===n)break;e=e.return}}function Nr(e,t){wo=e,$l=zr=null,e=e.dependencies,e!==null&&e.firstContext!==null&&((e.lanes&t)!==0&&(dt=!0),e.firstContext=null)}function Pt(e){var t=e._currentValue;if($l!==e)if(e={context:e,memoizedValue:t,next:null},zr===null){if(wo===null)throw Error(u(308));zr=e,wo.dependencies={lanes:0,firstContext:e}}else zr=zr.next=e;return t}var Yn=null;function Hl(e){Yn===null?Yn=[e]:Yn.push(e)}function iu(e,t,n,r){var i=t.interleaved;return i===null?(n.next=n,Hl(t)):(n.next=i.next,i.next=n),t.interleaved=n,an(e,r)}function an(e,t){e.lanes|=t;var n=e.alternate;for(n!==null&&(n.lanes|=t),n=e,e=e.return;e!==null;)e.childLanes|=t,n=e.alternate,n!==null&&(n.childLanes|=t),n=e,e=e.return;return n.tag===3?n.stateNode:null}var jn=!1;function Ql(e){e.updateQueue={baseState:e.memoizedState,firstBaseUpdate:null,lastBaseUpdate:null,shared:{pending:null,interleaved:null,lanes:0},effects:null}}function ou(e,t){e=e.updateQueue,t.updateQueue===e&&(t.updateQueue={baseState:e.baseState,firstBaseUpdate:e.firstBaseUpdate,lastBaseUpdate:e.lastBaseUpdate,shared:e.shared,effects:e.effects})}function sn(e,t){return{eventTime:e,lane:t,tag:0,payload:null,callback:null,next:null}}function zn(e,t,n){var r=e.updateQueue;if(r===null)return null;if(r=r.shared,(fe&2)!==0){var i=r.pending;return i===null?t.next=t:(t.next=i.next,i.next=t),r.pending=t,an(e,n)}return i=r.interleaved,i===null?(t.next=t,Hl(r)):(t.next=i.next,i.next=t),r.interleaved=t,an(e,n)}function ko(e,t,n){if(t=t.updateQueue,t!==null&&(t=t.shared,(n&4194240)!==0)){var r=t.lanes;r&=e.pendingLanes,n|=r,t.lanes=n,ll(e,n)}}function lu(e,t){var n=e.updateQueue,r=e.alternate;if(r!==null&&(r=r.updateQueue,n===r)){var i=null,l=null;if(n=n.firstBaseUpdate,n!==null){do{var s={eventTime:n.eventTime,lane:n.lane,tag:n.tag,payload:n.payload,callback:n.callback,next:null};l===null?i=l=s:l=l.next=s,n=n.next}while(n!==null);l===null?i=l=t:l=l.next=t}else i=l=t;n={baseState:r.baseState,firstBaseUpdate:i,lastBaseUpdate:l,shared:r.shared,effects:r.effects},e.updateQueue=n;return}e=n.lastBaseUpdate,e===null?n.firstBaseUpdate=t:e.next=t,n.lastBaseUpdate=t}function So(e,t,n,r){var i=e.updateQueue;jn=!1;var l=i.firstBaseUpdate,s=i.lastBaseUpdate,d=i.shared.pending;if(d!==null){i.shared.pending=null;var p=d,S=p.next;p.next=null,s===null?l=S:s.next=S,s=p;var C=e.alternate;C!==null&&(C=C.updateQueue,d=C.lastBaseUpdate,d!==s&&(d===null?C.firstBaseUpdate=S:d.next=S,C.lastBaseUpdate=p))}if(l!==null){var L=i.baseState;s=0,C=S=p=null,d=l;do{var z=d.lane,b=d.eventTime;if((r&z)===z){C!==null&&(C=C.next={eventTime:b,lane:0,tag:d.tag,payload:d.payload,callback:d.callback,next:null});e:{var W=e,Q=d;switch(z=t,b=n,Q.tag){case 1:if(W=Q.payload,typeof W=="function"){L=W.call(b,L,z);break e}L=W;break e;case 3:W.flags=W.flags&-65537|128;case 0:if(W=Q.payload,z=typeof W=="function"?W.call(b,L,z):W,z==null)break e;L=$({},L,z);break e;case 2:jn=!0}}d.callback!==null&&d.lane!==0&&(e.flags|=64,z=i.effects,z===null?i.effects=[d]:z.push(d))}else b={eventTime:b,lane:z,tag:d.tag,payload:d.payload,callback:d.callback,next:null},C===null?(S=C=b,p=L):C=C.next=b,s|=z;if(d=d.next,d===null){if(d=i.shared.pending,d===null)break;z=d,d=z.next,z.next=null,i.lastBaseUpdate=z,i.shared.pending=null}}while(!0);if(C===null&&(p=L),i.baseState=p,i.firstBaseUpdate=S,i.lastBaseUpdate=C,t=i.shared.interleaved,t!==null){i=t;do s|=i.lane,i=i.next;while(i!==t)}else l===null&&(i.shared.lanes=0);Xn|=s,e.lanes=s,e.memoizedState=L}}function au(e,t,n){if(e=t.effects,t.effects=null,e!==null)for(t=0;t<e.length;t++){var r=e[t],i=r.callback;if(i!==null){if(r.callback=null,r=n,typeof i!="function")throw Error(u(191,i));i.call(r)}}}var ui={},Qt=kn(ui),ci=kn(ui),di=kn(ui);function qn(e){if(e===ui)throw Error(u(174));return e}function Kl(e,t){switch(Ne(di,t),Ne(ci,e),Ne(Qt,ui),e=t.nodeType,e){case 9:case 11:t=(t=t.documentElement)?t.namespaceURI:In(null,"");break;default:e=e===8?t.parentNode:t,t=e.namespaceURI||null,e=e.tagName,t=In(t,e)}De(Qt),Ne(Qt,t)}function Cr(){De(Qt),De(ci),De(di)}function su(e){qn(di.current);var t=qn(Qt.current),n=In(t,e.type);t!==n&&(Ne(ci,e),Ne(Qt,n))}function Yl(e){ci.current===e&&(De(Qt),De(ci))}var Pe=kn(0);function _o(e){for(var t=e;t!==null;){if(t.tag===13){var n=t.memoizedState;if(n!==null&&(n=n.dehydrated,n===null||n.data==="$?"||n.data==="$!"))return t}else if(t.tag===19&&t.memoizedProps.revealOrder!==void 0){if((t.flags&128)!==0)return t}else if(t.child!==null){t.child.return=t,t=t.child;continue}if(t===e)break;for(;t.sibling===null;){if(t.return===null||t.return===e)return null;t=t.return}t.sibling.return=t.return,t=t.sibling}return null}var ql=[];function Gl(){for(var e=0;e<ql.length;e++)ql[e]._workInProgressVersionPrimary=null;ql.length=0}var jo=pe.ReactCurrentDispatcher,Xl=pe.ReactCurrentBatchConfig,Gn=0,Te=null,Ae=null,Ve=null,zo=!1,fi=!1,pi=0,wf=0;function Je(){throw Error(u(321))}function Zl(e,t){if(t===null)return!1;for(var n=0;n<t.length&&n<e.length;n++)if(!At(e[n],t[n]))return!1;return!0}function Jl(e,t,n,r,i,l){if(Gn=l,Te=t,t.memoizedState=null,t.updateQueue=null,t.lanes=0,jo.current=e===null||e.memoizedState===null?jf:zf,e=n(r,i),fi){l=0;do{if(fi=!1,pi=0,25<=l)throw Error(u(301));l+=1,Ve=Ae=null,t.updateQueue=null,jo.current=Nf,e=n(r,i)}while(fi)}if(jo.current=Eo,t=Ae!==null&&Ae.next!==null,Gn=0,Ve=Ae=Te=null,zo=!1,t)throw Error(u(300));return e}function ea(){var e=pi!==0;return pi=0,e}function Kt(){var e={memoizedState:null,baseState:null,baseQueue:null,queue:null,next:null};return Ve===null?Te.memoizedState=Ve=e:Ve=Ve.next=e,Ve}function Tt(){if(Ae===null){var e=Te.alternate;e=e!==null?e.memoizedState:null}else e=Ae.next;var t=Ve===null?Te.memoizedState:Ve.next;if(t!==null)Ve=t,Ae=e;else{if(e===null)throw Error(u(310));Ae=e,e={memoizedState:Ae.memoizedState,baseState:Ae.baseState,baseQueue:Ae.baseQueue,queue:Ae.queue,next:null},Ve===null?Te.memoizedState=Ve=e:Ve=Ve.next=e}return Ve}function hi(e,t){return typeof t=="function"?t(e):t}function ta(e){var t=Tt(),n=t.queue;if(n===null)throw Error(u(311));n.lastRenderedReducer=e;var r=Ae,i=r.baseQueue,l=n.pending;if(l!==null){if(i!==null){var s=i.next;i.next=l.next,l.next=s}r.baseQueue=i=l,n.pending=null}if(i!==null){l=i.next,r=r.baseState;var d=s=null,p=null,S=l;do{var C=S.lane;if((Gn&C)===C)p!==null&&(p=p.next={lane:0,action:S.action,hasEagerState:S.hasEagerState,eagerState:S.eagerState,next:null}),r=S.hasEagerState?S.eagerState:e(r,S.action);else{var L={lane:C,action:S.action,hasEagerState:S.hasEagerState,eagerState:S.eagerState,next:null};p===null?(d=p=L,s=r):p=p.next=L,Te.lanes|=C,Xn|=C}S=S.next}while(S!==null&&S!==l);p===null?s=r:p.next=d,At(r,t.memoizedState)||(dt=!0),t.memoizedState=r,t.baseState=s,t.baseQueue=p,n.lastRenderedState=r}if(e=n.interleaved,e!==null){i=e;do l=i.lane,Te.lanes|=l,Xn|=l,i=i.next;while(i!==e)}else i===null&&(n.lanes=0);return[t.memoizedState,n.dispatch]}function na(e){var t=Tt(),n=t.queue;if(n===null)throw Error(u(311));n.lastRenderedReducer=e;var r=n.dispatch,i=n.pending,l=t.memoizedState;if(i!==null){n.pending=null;var s=i=i.next;do l=e(l,s.action),s=s.next;while(s!==i);At(l,t.memoizedState)||(dt=!0),t.memoizedState=l,t.baseQueue===null&&(t.baseState=l),n.lastRenderedState=l}return[l,r]}function uu(){}function cu(e,t){var n=Te,r=Tt(),i=t(),l=!At(r.memoizedState,i);if(l&&(r.memoizedState=i,dt=!0),r=r.queue,ra(pu.bind(null,n,r,e),[e]),r.getSnapshot!==t||l||Ve!==null&&Ve.memoizedState.tag&1){if(n.flags|=2048,gi(9,fu.bind(null,n,r,i,t),void 0,null),Be===null)throw Error(u(349));(Gn&30)!==0||du(n,t,i)}return i}function du(e,t,n){e.flags|=16384,e={getSnapshot:t,value:n},t=Te.updateQueue,t===null?(t={lastEffect:null,stores:null},Te.updateQueue=t,t.stores=[e]):(n=t.stores,n===null?t.stores=[e]:n.push(e))}function fu(e,t,n,r){t.value=n,t.getSnapshot=r,hu(t)&&gu(e)}function pu(e,t,n){return n(function(){hu(t)&&gu(e)})}function hu(e){var t=e.getSnapshot;e=e.value;try{var n=t();return!At(e,n)}catch{return!0}}function gu(e){var t=an(e,1);t!==null&&Bt(t,e,1,-1)}function mu(e){var t=Kt();return typeof e=="function"&&(e=e()),t.memoizedState=t.baseState=e,e={pending:null,interleaved:null,lanes:0,dispatch:null,lastRenderedReducer:hi,lastRenderedState:e},t.queue=e,e=e.dispatch=_f.bind(null,Te,e),[t.memoizedState,e]}function gi(e,t,n,r){return e={tag:e,create:t,destroy:n,deps:r,next:null},t=Te.updateQueue,t===null?(t={lastEffect:null,stores:null},Te.updateQueue=t,t.lastEffect=e.next=e):(n=t.lastEffect,n===null?t.lastEffect=e.next=e:(r=n.next,n.next=e,e.next=r,t.lastEffect=e)),e}function vu(){return Tt().memoizedState}function No(e,t,n,r){var i=Kt();Te.flags|=e,i.memoizedState=gi(1|t,n,void 0,r===void 0?null:r)}function Co(e,t,n,r){var i=Tt();r=r===void 0?null:r;var l=void 0;if(Ae!==null){var s=Ae.memoizedState;if(l=s.destroy,r!==null&&Zl(r,s.deps)){i.memoizedState=gi(t,n,l,r);return}}Te.flags|=e,i.memoizedState=gi(1|t,n,l,r)}function yu(e,t){return No(8390656,8,e,t)}function ra(e,t){return Co(2048,8,e,t)}function xu(e,t){return Co(4,2,e,t)}function wu(e,t){return Co(4,4,e,t)}function ku(e,t){if(typeof t=="function")return e=e(),t(e),function(){t(null)};if(t!=null)return e=e(),t.current=e,function(){t.current=null}}function Su(e,t,n){return n=n!=null?n.concat([e]):null,Co(4,4,ku.bind(null,t,e),n)}function ia(){}function _u(e,t){var n=Tt();t=t===void 0?null:t;var r=n.memoizedState;return r!==null&&t!==null&&Zl(t,r[1])?r[0]:(n.memoizedState=[e,t],e)}function ju(e,t){var n=Tt();t=t===void 0?null:t;var r=n.memoizedState;return r!==null&&t!==null&&Zl(t,r[1])?r[0]:(e=e(),n.memoizedState=[e,t],e)}function zu(e,t,n){return(Gn&21)===0?(e.baseState&&(e.baseState=!1,dt=!0),e.memoizedState=n):(At(n,t)||(n=ts(),Te.lanes|=n,Xn|=n,e.baseState=!0),t)}function kf(e,t){var n=we;we=n!==0&&4>n?n:4,e(!0);var r=Xl.transition;Xl.transition={};try{e(!1),t()}finally{we=n,Xl.transition=r}}function Nu(){return Tt().memoizedState}function Sf(e,t,n){var r=Dn(e);if(n={lane:r,action:n,hasEagerState:!1,eagerState:null,next:null},Cu(e))Eu(t,n);else if(n=iu(e,t,n,r),n!==null){var i=ot();Bt(n,e,r,i),Du(n,t,r)}}function _f(e,t,n){var r=Dn(e),i={lane:r,action:n,hasEagerState:!1,eagerState:null,next:null};if(Cu(e))Eu(t,i);else{var l=e.alternate;if(e.lanes===0&&(l===null||l.lanes===0)&&(l=t.lastRenderedReducer,l!==null))try{var s=t.lastRenderedState,d=l(s,n);if(i.hasEagerState=!0,i.eagerState=d,At(d,s)){var p=t.interleaved;p===null?(i.next=i,Hl(t)):(i.next=p.next,p.next=i),t.interleaved=i;return}}catch{}finally{}n=iu(e,t,i,r),n!==null&&(i=ot(),Bt(n,e,r,i),Du(n,t,r))}}function Cu(e){var t=e.alternate;return e===Te||t!==null&&t===Te}function Eu(e,t){fi=zo=!0;var n=e.pending;n===null?t.next=t:(t.next=n.next,n.next=t),e.pending=t}function Du(e,t,n){if((n&4194240)!==0){var r=t.lanes;r&=e.pendingLanes,n|=r,t.lanes=n,ll(e,n)}}var Eo={readContext:Pt,useCallback:Je,useContext:Je,useEffect:Je,useImperativeHandle:Je,useInsertionEffect:Je,useLayoutEffect:Je,useMemo:Je,useReducer:Je,useRef:Je,useState:Je,useDebugValue:Je,useDeferredValue:Je,useTransition:Je,useMutableSource:Je,useSyncExternalStore:Je,useId:Je,unstable_isNewReconciler:!1},jf={readContext:Pt,useCallback:function(e,t){return Kt().memoizedState=[e,t===void 0?null:t],e},useContext:Pt,useEffect:yu,useImperativeHandle:function(e,t,n){return n=n!=null?n.concat([e]):null,No(4194308,4,ku.bind(null,t,e),n)},useLayoutEffect:function(e,t){return No(4194308,4,e,t)},useInsertionEffect:function(e,t){return No(4,2,e,t)},useMemo:function(e,t){var n=Kt();return t=t===void 0?null:t,e=e(),n.memoizedState=[e,t],e},useReducer:function(e,t,n){var r=Kt();return t=n!==void 0?n(t):t,r.memoizedState=r.baseState=t,e={pending:null,interleaved:null,lanes:0,dispatch:null,lastRenderedReducer:e,lastRenderedState:t},r.queue=e,e=e.dispatch=Sf.bind(null,Te,e),[r.memoizedState,e]},useRef:function(e){var t=Kt();return e={current:e},t.memoizedState=e},useState:mu,useDebugValue:ia,useDeferredValue:function(e){return Kt().memoizedState=e},useTransition:function(){var e=mu(!1),t=e[0];return e=kf.bind(null,e[1]),Kt().memoizedState=e,[t,e]},useMutableSource:function(){},useSyncExternalStore:function(e,t,n){var r=Te,i=Kt();if(Le){if(n===void 0)throw Error(u(407));n=n()}else{if(n=t(),Be===null)throw Error(u(349));(Gn&30)!==0||du(r,t,n)}i.memoizedState=n;var l={value:n,getSnapshot:t};return i.queue=l,yu(pu.bind(null,r,l,e),[e]),r.flags|=2048,gi(9,fu.bind(null,r,l,n,t),void 0,null),n},useId:function(){var e=Kt(),t=Be.identifierPrefix;if(Le){var n=ln,r=on;n=(r&~(1<<32-st(r)-1)).toString(32)+n,t=":"+t+"R"+n,n=pi++,0<n&&(t+="H"+n.toString(32)),t+=":"}else n=wf++,t=":"+t+"r"+n.toString(32)+":";return e.memoizedState=t},unstable_isNewReconciler:!1},zf={readContext:Pt,useCallback:_u,useContext:Pt,useEffect:ra,useImperativeHandle:Su,useInsertionEffect:xu,useLayoutEffect:wu,useMemo:ju,useReducer:ta,useRef:vu,useState:function(){return ta(hi)},useDebugValue:ia,useDeferredValue:function(e){var t=Tt();return zu(t,Ae.memoizedState,e)},useTransition:function(){var e=ta(hi)[0],t=Tt().memoizedState;return[e,t]},useMutableSource:uu,useSyncExternalStore:cu,useId:Nu,unstable_isNewReconciler:!1},Nf={readContext:Pt,useCallback:_u,useContext:Pt,useEffect:ra,useImperativeHandle:Su,useInsertionEffect:xu,useLayoutEffect:wu,useMemo:ju,useReducer:na,useRef:vu,useState:function(){return na(hi)},useDebugValue:ia,useDeferredValue:function(e){var t=Tt();return Ae===null?t.memoizedState=e:zu(t,Ae.memoizedState,e)},useTransition:function(){var e=na(hi)[0],t=Tt().memoizedState;return[e,t]},useMutableSource:uu,useSyncExternalStore:cu,useId:Nu,unstable_isNewReconciler:!1};function Ut(e,t){if(e&&e.defaultProps){t=$({},t),e=e.defaultProps;for(var n in e)t[n]===void 0&&(t[n]=e[n]);return t}return t}function oa(e,t,n,r){t=e.memoizedState,n=n(r,t),n=n==null?t:$({},t,n),e.memoizedState=n,e.lanes===0&&(e.updateQueue.baseState=n)}var Do={isMounted:function(e){return(e=e._reactInternals)?en(e)===e:!1},enqueueSetState:function(e,t,n){e=e._reactInternals;var r=ot(),i=Dn(e),l=sn(r,i);l.payload=t,n!=null&&(l.callback=n),t=zn(e,l,i),t!==null&&(Bt(t,e,i,r),ko(t,e,i))},enqueueReplaceState:function(e,t,n){e=e._reactInternals;var r=ot(),i=Dn(e),l=sn(r,i);l.tag=1,l.payload=t,n!=null&&(l.callback=n),t=zn(e,l,i),t!==null&&(Bt(t,e,i,r),ko(t,e,i))},enqueueForceUpdate:function(e,t){e=e._reactInternals;var n=ot(),r=Dn(e),i=sn(n,r);i.tag=2,t!=null&&(i.callback=t),t=zn(e,i,r),t!==null&&(Bt(t,e,r,n),ko(t,e,r))}};function Lu(e,t,n,r,i,l,s){return e=e.stateNode,typeof e.shouldComponentUpdate=="function"?e.shouldComponentUpdate(r,l,s):t.prototype&&t.prototype.isPureReactComponent?!ti(n,r)||!ti(i,l):!0}function Pu(e,t,n){var r=!1,i=Sn,l=t.contextType;return typeof l=="object"&&l!==null?l=Pt(l):(i=ct(t)?Hn:Ze.current,r=t.contextTypes,l=(r=r!=null)?wr(e,i):Sn),t=new t(n,l),e.memoizedState=t.state!==null&&t.state!==void 0?t.state:null,t.updater=Do,e.stateNode=t,t._reactInternals=e,r&&(e=e.stateNode,e.__reactInternalMemoizedUnmaskedChildContext=i,e.__reactInternalMemoizedMaskedChildContext=l),t}function Tu(e,t,n,r){e=t.state,typeof t.componentWillReceiveProps=="function"&&t.componentWillReceiveProps(n,r),typeof t.UNSAFE_componentWillReceiveProps=="function"&&t.UNSAFE_componentWillReceiveProps(n,r),t.state!==e&&Do.enqueueReplaceState(t,t.state,null)}function la(e,t,n,r){var i=e.stateNode;i.props=n,i.state=e.memoizedState,i.refs={},Ql(e);var l=t.contextType;typeof l=="object"&&l!==null?i.context=Pt(l):(l=ct(t)?Hn:Ze.current,i.context=wr(e,l)),i.state=e.memoizedState,l=t.getDerivedStateFromProps,typeof l=="function"&&(oa(e,t,l,n),i.state=e.memoizedState),typeof t.getDerivedStateFromProps=="function"||typeof i.getSnapshotBeforeUpdate=="function"||typeof i.UNSAFE_componentWillMount!="function"&&typeof i.componentWillMount!="function"||(t=i.state,typeof i.componentWillMount=="function"&&i.componentWillMount(),typeof i.UNSAFE_componentWillMount=="function"&&i.UNSAFE_componentWillMount(),t!==i.state&&Do.enqueueReplaceState(i,i.state,null),So(e,n,i,r),i.state=e.memoizedState),typeof i.componentDidMount=="function"&&(e.flags|=4194308)}function Er(e,t){try{var n="",r=t;do n+=ce(r),r=r.return;while(r);var i=n}catch(l){i=`
Error generating stack: `+l.message+`
`+l.stack}return{value:e,source:t,stack:i,digest:null}}function aa(e,t,n){return{value:e,source:null,stack:n??null,digest:t??null}}function sa(e,t){try{console.error(t.value)}catch(n){setTimeout(function(){throw n})}}var Cf=typeof WeakMap=="function"?WeakMap:Map;function Mu(e,t,n){n=sn(-1,n),n.tag=3,n.payload={element:null};var r=t.value;return n.callback=function(){Oo||(Oo=!0,_a=r),sa(e,t)},n}function Fu(e,t,n){n=sn(-1,n),n.tag=3;var r=e.type.getDerivedStateFromError;if(typeof r=="function"){var i=t.value;n.payload=function(){return r(i)},n.callback=function(){sa(e,t)}}var l=e.stateNode;return l!==null&&typeof l.componentDidCatch=="function"&&(n.callback=function(){sa(e,t),typeof r!="function"&&(Cn===null?Cn=new Set([this]):Cn.add(this));var s=t.stack;this.componentDidCatch(t.value,{componentStack:s!==null?s:""})}),n}function Ru(e,t,n){var r=e.pingCache;if(r===null){r=e.pingCache=new Cf;var i=new Set;r.set(t,i)}else i=r.get(t),i===void 0&&(i=new Set,r.set(t,i));i.has(n)||(i.add(n),e=$f.bind(null,e,t,n),t.then(e,e))}function Ou(e){do{var t;if((t=e.tag===13)&&(t=e.memoizedState,t=t!==null?t.dehydrated!==null:!0),t)return e;e=e.return}while(e!==null);return null}function Iu(e,t,n,r,i){return(e.mode&1)===0?(e===t?e.flags|=65536:(e.flags|=128,n.flags|=131072,n.flags&=-52805,n.tag===1&&(n.alternate===null?n.tag=17:(t=sn(-1,1),t.tag=2,zn(n,t,1))),n.lanes|=1),e):(e.flags|=65536,e.lanes=i,e)}var Ef=pe.ReactCurrentOwner,dt=!1;function it(e,t,n,r){t.child=e===null?ru(t,null,n,r):jr(t,e.child,n,r)}function Au(e,t,n,r,i){n=n.render;var l=t.ref;return Nr(t,i),r=Jl(e,t,n,r,l,i),n=ea(),e!==null&&!dt?(t.updateQueue=e.updateQueue,t.flags&=-2053,e.lanes&=~i,un(e,t,i)):(Le&&n&&Ol(t),t.flags|=1,it(e,t,r,i),t.child)}function bu(e,t,n,r,i){if(e===null){var l=n.type;return typeof l=="function"&&!La(l)&&l.defaultProps===void 0&&n.compare===null&&n.defaultProps===void 0?(t.tag=15,t.type=l,Uu(e,t,l,r,i)):(e=Vo(n.type,null,r,t,t.mode,i),e.ref=t.ref,e.return=t,t.child=e)}if(l=e.child,(e.lanes&i)===0){var s=l.memoizedProps;if(n=n.compare,n=n!==null?n:ti,n(s,r)&&e.ref===t.ref)return un(e,t,i)}return t.flags|=1,e=Pn(l,r),e.ref=t.ref,e.return=t,t.child=e}function Uu(e,t,n,r,i){if(e!==null){var l=e.memoizedProps;if(ti(l,r)&&e.ref===t.ref)if(dt=!1,t.pendingProps=r=l,(e.lanes&i)!==0)(e.flags&131072)!==0&&(dt=!0);else return t.lanes=e.lanes,un(e,t,i)}return ua(e,t,n,r,i)}function $u(e,t,n){var r=t.pendingProps,i=r.children,l=e!==null?e.memoizedState:null;if(r.mode==="hidden")if((t.mode&1)===0)t.memoizedState={baseLanes:0,cachePool:null,transitions:null},Ne(Lr,St),St|=n;else{if((n&1073741824)===0)return e=l!==null?l.baseLanes|n:n,t.lanes=t.childLanes=1073741824,t.memoizedState={baseLanes:e,cachePool:null,transitions:null},t.updateQueue=null,Ne(Lr,St),St|=e,null;t.memoizedState={baseLanes:0,cachePool:null,transitions:null},r=l!==null?l.baseLanes:n,Ne(Lr,St),St|=r}else l!==null?(r=l.baseLanes|n,t.memoizedState=null):r=n,Ne(Lr,St),St|=r;return it(e,t,i,n),t.child}function Vu(e,t){var n=t.ref;(e===null&&n!==null||e!==null&&e.ref!==n)&&(t.flags|=512,t.flags|=2097152)}function ua(e,t,n,r,i){var l=ct(n)?Hn:Ze.current;return l=wr(t,l),Nr(t,i),n=Jl(e,t,n,r,l,i),r=ea(),e!==null&&!dt?(t.updateQueue=e.updateQueue,t.flags&=-2053,e.lanes&=~i,un(e,t,i)):(Le&&r&&Ol(t),t.flags|=1,it(e,t,n,i),t.child)}function Bu(e,t,n,r,i){if(ct(n)){var l=!0;po(t)}else l=!1;if(Nr(t,i),t.stateNode===null)Po(e,t),Pu(t,n,r),la(t,n,r,i),r=!0;else if(e===null){var s=t.stateNode,d=t.memoizedProps;s.props=d;var p=s.context,S=n.contextType;typeof S=="object"&&S!==null?S=Pt(S):(S=ct(n)?Hn:Ze.current,S=wr(t,S));var C=n.getDerivedStateFromProps,L=typeof C=="function"||typeof s.getSnapshotBeforeUpdate=="function";L||typeof s.UNSAFE_componentWillReceiveProps!="function"&&typeof s.componentWillReceiveProps!="function"||(d!==r||p!==S)&&Tu(t,s,r,S),jn=!1;var z=t.memoizedState;s.state=z,So(t,r,s,i),p=t.memoizedState,d!==r||z!==p||ut.current||jn?(typeof C=="function"&&(oa(t,n,C,r),p=t.memoizedState),(d=jn||Lu(t,n,d,r,z,p,S))?(L||typeof s.UNSAFE_componentWillMount!="function"&&typeof s.componentWillMount!="function"||(typeof s.componentWillMount=="function"&&s.componentWillMount(),typeof s.UNSAFE_componentWillMount=="function"&&s.UNSAFE_componentWillMount()),typeof s.componentDidMount=="function"&&(t.flags|=4194308)):(typeof s.componentDidMount=="function"&&(t.flags|=4194308),t.memoizedProps=r,t.memoizedState=p),s.props=r,s.state=p,s.context=S,r=d):(typeof s.componentDidMount=="function"&&(t.flags|=4194308),r=!1)}else{s=t.stateNode,ou(e,t),d=t.memoizedProps,S=t.type===t.elementType?d:Ut(t.type,d),s.props=S,L=t.pendingProps,z=s.context,p=n.contextType,typeof p=="object"&&p!==null?p=Pt(p):(p=ct(n)?Hn:Ze.current,p=wr(t,p));var b=n.getDerivedStateFromProps;(C=typeof b=="function"||typeof s.getSnapshotBeforeUpdate=="function")||typeof s.UNSAFE_componentWillReceiveProps!="function"&&typeof s.componentWillReceiveProps!="function"||(d!==L||z!==p)&&Tu(t,s,r,p),jn=!1,z=t.memoizedState,s.state=z,So(t,r,s,i);var W=t.memoizedState;d!==L||z!==W||ut.current||jn?(typeof b=="function"&&(oa(t,n,b,r),W=t.memoizedState),(S=jn||Lu(t,n,S,r,z,W,p)||!1)?(C||typeof s.UNSAFE_componentWillUpdate!="function"&&typeof s.componentWillUpdate!="function"||(typeof s.componentWillUpdate=="function"&&s.componentWillUpdate(r,W,p),typeof s.UNSAFE_componentWillUpdate=="function"&&s.UNSAFE_componentWillUpdate(r,W,p)),typeof s.componentDidUpdate=="function"&&(t.flags|=4),typeof s.getSnapshotBeforeUpdate=="function"&&(t.flags|=1024)):(typeof s.componentDidUpdate!="function"||d===e.memoizedProps&&z===e.memoizedState||(t.flags|=4),typeof s.getSnapshotBeforeUpdate!="function"||d===e.memoizedProps&&z===e.memoizedState||(t.flags|=1024),t.memoizedProps=r,t.memoizedState=W),s.props=r,s.state=W,s.context=p,r=S):(typeof s.componentDidUpdate!="function"||d===e.memoizedProps&&z===e.memoizedState||(t.flags|=4),typeof s.getSnapshotBeforeUpdate!="function"||d===e.memoizedProps&&z===e.memoizedState||(t.flags|=1024),r=!1)}return ca(e,t,n,r,l,i)}function ca(e,t,n,r,i,l){Vu(e,t);var s=(t.flags&128)!==0;if(!r&&!s)return i&&Ys(t,n,!1),un(e,t,l);r=t.stateNode,Ef.current=t;var d=s&&typeof n.getDerivedStateFromError!="function"?null:r.render();return t.flags|=1,e!==null&&s?(t.child=jr(t,e.child,null,l),t.child=jr(t,null,d,l)):it(e,t,d,l),t.memoizedState=r.state,i&&Ys(t,n,!0),t.child}function Wu(e){var t=e.stateNode;t.pendingContext?Qs(e,t.pendingContext,t.pendingContext!==t.context):t.context&&Qs(e,t.context,!1),Kl(e,t.containerInfo)}function Hu(e,t,n,r,i){return _r(),Ul(i),t.flags|=256,it(e,t,n,r),t.child}var da={dehydrated:null,treeContext:null,retryLane:0};function fa(e){return{baseLanes:e,cachePool:null,transitions:null}}function Qu(e,t,n){var r=t.pendingProps,i=Pe.current,l=!1,s=(t.flags&128)!==0,d;if((d=s)||(d=e!==null&&e.memoizedState===null?!1:(i&2)!==0),d?(l=!0,t.flags&=-129):(e===null||e.memoizedState!==null)&&(i|=1),Ne(Pe,i&1),e===null)return bl(t),e=t.memoizedState,e!==null&&(e=e.dehydrated,e!==null)?((t.mode&1)===0?t.lanes=1:e.data==="$!"?t.lanes=8:t.lanes=1073741824,null):(s=r.children,e=r.fallback,l?(r=t.mode,l=t.child,s={mode:"hidden",children:s},(r&1)===0&&l!==null?(l.childLanes=0,l.pendingProps=s):l=Bo(s,r,0,null),e=tr(e,r,n,null),l.return=t,e.return=t,l.sibling=e,t.child=l,t.child.memoizedState=fa(n),t.memoizedState=da,e):pa(t,s));if(i=e.memoizedState,i!==null&&(d=i.dehydrated,d!==null))return Df(e,t,s,r,d,i,n);if(l){l=r.fallback,s=t.mode,i=e.child,d=i.sibling;var p={mode:"hidden",children:r.children};return(s&1)===0&&t.child!==i?(r=t.child,r.childLanes=0,r.pendingProps=p,t.deletions=null):(r=Pn(i,p),r.subtreeFlags=i.subtreeFlags&14680064),d!==null?l=Pn(d,l):(l=tr(l,s,n,null),l.flags|=2),l.return=t,r.return=t,r.sibling=l,t.child=r,r=l,l=t.child,s=e.child.memoizedState,s=s===null?fa(n):{baseLanes:s.baseLanes|n,cachePool:null,transitions:s.transitions},l.memoizedState=s,l.childLanes=e.childLanes&~n,t.memoizedState=da,r}return l=e.child,e=l.sibling,r=Pn(l,{mode:"visible",children:r.children}),(t.mode&1)===0&&(r.lanes=n),r.return=t,r.sibling=null,e!==null&&(n=t.deletions,n===null?(t.deletions=[e],t.flags|=16):n.push(e)),t.child=r,t.memoizedState=null,r}function pa(e,t){return t=Bo({mode:"visible",children:t},e.mode,0,null),t.return=e,e.child=t}function Lo(e,t,n,r){return r!==null&&Ul(r),jr(t,e.child,null,n),e=pa(t,t.pendingProps.children),e.flags|=2,t.memoizedState=null,e}function Df(e,t,n,r,i,l,s){if(n)return t.flags&256?(t.flags&=-257,r=aa(Error(u(422))),Lo(e,t,s,r)):t.memoizedState!==null?(t.child=e.child,t.flags|=128,null):(l=r.fallback,i=t.mode,r=Bo({mode:"visible",children:r.children},i,0,null),l=tr(l,i,s,null),l.flags|=2,r.return=t,l.return=t,r.sibling=l,t.child=r,(t.mode&1)!==0&&jr(t,e.child,null,s),t.child.memoizedState=fa(s),t.memoizedState=da,l);if((t.mode&1)===0)return Lo(e,t,s,null);if(i.data==="$!"){if(r=i.nextSibling&&i.nextSibling.dataset,r)var d=r.dgst;return r=d,l=Error(u(419)),r=aa(l,r,void 0),Lo(e,t,s,r)}if(d=(s&e.childLanes)!==0,dt||d){if(r=Be,r!==null){switch(s&-s){case 4:i=2;break;case 16:i=8;break;case 64:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:case 4194304:case 8388608:case 16777216:case 33554432:case 67108864:i=32;break;case 536870912:i=268435456;break;default:i=0}i=(i&(r.suspendedLanes|s))!==0?0:i,i!==0&&i!==l.retryLane&&(l.retryLane=i,an(e,i),Bt(r,e,i,-1))}return Da(),r=aa(Error(u(421))),Lo(e,t,s,r)}return i.data==="$?"?(t.flags|=128,t.child=e.child,t=Vf.bind(null,e),i._reactRetry=t,null):(e=l.treeContext,kt=wn(i.nextSibling),wt=t,Le=!0,bt=null,e!==null&&(Dt[Lt++]=on,Dt[Lt++]=ln,Dt[Lt++]=Qn,on=e.id,ln=e.overflow,Qn=t),t=pa(t,r.children),t.flags|=4096,t)}function Ku(e,t,n){e.lanes|=t;var r=e.alternate;r!==null&&(r.lanes|=t),Wl(e.return,t,n)}function ha(e,t,n,r,i){var l=e.memoizedState;l===null?e.memoizedState={isBackwards:t,rendering:null,renderingStartTime:0,last:r,tail:n,tailMode:i}:(l.isBackwards=t,l.rendering=null,l.renderingStartTime=0,l.last=r,l.tail=n,l.tailMode=i)}function Yu(e,t,n){var r=t.pendingProps,i=r.revealOrder,l=r.tail;if(it(e,t,r.children,n),r=Pe.current,(r&2)!==0)r=r&1|2,t.flags|=128;else{if(e!==null&&(e.flags&128)!==0)e:for(e=t.child;e!==null;){if(e.tag===13)e.memoizedState!==null&&Ku(e,n,t);else if(e.tag===19)Ku(e,n,t);else if(e.child!==null){e.child.return=e,e=e.child;continue}if(e===t)break e;for(;e.sibling===null;){if(e.return===null||e.return===t)break e;e=e.return}e.sibling.return=e.return,e=e.sibling}r&=1}if(Ne(Pe,r),(t.mode&1)===0)t.memoizedState=null;else switch(i){case"forwards":for(n=t.child,i=null;n!==null;)e=n.alternate,e!==null&&_o(e)===null&&(i=n),n=n.sibling;n=i,n===null?(i=t.child,t.child=null):(i=n.sibling,n.sibling=null),ha(t,!1,i,n,l);break;case"backwards":for(n=null,i=t.child,t.child=null;i!==null;){if(e=i.alternate,e!==null&&_o(e)===null){t.child=i;break}e=i.sibling,i.sibling=n,n=i,i=e}ha(t,!0,n,null,l);break;case"together":ha(t,!1,null,null,void 0);break;default:t.memoizedState=null}return t.child}function Po(e,t){(t.mode&1)===0&&e!==null&&(e.alternate=null,t.alternate=null,t.flags|=2)}function un(e,t,n){if(e!==null&&(t.dependencies=e.dependencies),Xn|=t.lanes,(n&t.childLanes)===0)return null;if(e!==null&&t.child!==e.child)throw Error(u(153));if(t.child!==null){for(e=t.child,n=Pn(e,e.pendingProps),t.child=n,n.return=t;e.sibling!==null;)e=e.sibling,n=n.sibling=Pn(e,e.pendingProps),n.return=t;n.sibling=null}return t.child}function Lf(e,t,n){switch(t.tag){case 3:Wu(t),_r();break;case 5:su(t);break;case 1:ct(t.type)&&po(t);break;case 4:Kl(t,t.stateNode.containerInfo);break;case 10:var r=t.type._context,i=t.memoizedProps.value;Ne(xo,r._currentValue),r._currentValue=i;break;case 13:if(r=t.memoizedState,r!==null)return r.dehydrated!==null?(Ne(Pe,Pe.current&1),t.flags|=128,null):(n&t.child.childLanes)!==0?Qu(e,t,n):(Ne(Pe,Pe.current&1),e=un(e,t,n),e!==null?e.sibling:null);Ne(Pe,Pe.current&1);break;case 19:if(r=(n&t.childLanes)!==0,(e.flags&128)!==0){if(r)return Yu(e,t,n);t.flags|=128}if(i=t.memoizedState,i!==null&&(i.rendering=null,i.tail=null,i.lastEffect=null),Ne(Pe,Pe.current),r)break;return null;case 22:case 23:return t.lanes=0,$u(e,t,n)}return un(e,t,n)}var qu,ga,Gu,Xu;qu=function(e,t){for(var n=t.child;n!==null;){if(n.tag===5||n.tag===6)e.appendChild(n.stateNode);else if(n.tag!==4&&n.child!==null){n.child.return=n,n=n.child;continue}if(n===t)break;for(;n.sibling===null;){if(n.return===null||n.return===t)return;n=n.return}n.sibling.return=n.return,n=n.sibling}},ga=function(){},Gu=function(e,t,n,r){var i=e.memoizedProps;if(i!==r){e=t.stateNode,qn(Qt.current);var l=null;switch(n){case"input":i=Rt(e,i),r=Rt(e,r),l=[];break;case"select":i=$({},i,{value:void 0}),r=$({},r,{value:void 0}),l=[];break;case"textarea":i=at(e,i),r=at(e,r),l=[];break;default:typeof i.onClick!="function"&&typeof r.onClick=="function"&&(e.onclick=uo)}Fi(n,r);var s;n=null;for(S in i)if(!r.hasOwnProperty(S)&&i.hasOwnProperty(S)&&i[S]!=null)if(S==="style"){var d=i[S];for(s in d)d.hasOwnProperty(s)&&(n||(n={}),n[s]="")}else S!=="dangerouslySetInnerHTML"&&S!=="children"&&S!=="suppressContentEditableWarning"&&S!=="suppressHydrationWarning"&&S!=="autoFocus"&&(g.hasOwnProperty(S)?l||(l=[]):(l=l||[]).push(S,null));for(S in r){var p=r[S];if(d=i!=null?i[S]:void 0,r.hasOwnProperty(S)&&p!==d&&(p!=null||d!=null))if(S==="style")if(d){for(s in d)!d.hasOwnProperty(s)||p&&p.hasOwnProperty(s)||(n||(n={}),n[s]="");for(s in p)p.hasOwnProperty(s)&&d[s]!==p[s]&&(n||(n={}),n[s]=p[s])}else n||(l||(l=[]),l.push(S,n)),n=p;else S==="dangerouslySetInnerHTML"?(p=p?p.__html:void 0,d=d?d.__html:void 0,p!=null&&d!==p&&(l=l||[]).push(S,p)):S==="children"?typeof p!="string"&&typeof p!="number"||(l=l||[]).push(S,""+p):S!=="suppressContentEditableWarning"&&S!=="suppressHydrationWarning"&&(g.hasOwnProperty(S)?(p!=null&&S==="onScroll"&&Ee("scroll",e),l||d===p||(l=[])):(l=l||[]).push(S,p))}n&&(l=l||[]).push("style",n);var S=l;(t.updateQueue=S)&&(t.flags|=4)}},Xu=function(e,t,n,r){n!==r&&(t.flags|=4)};function mi(e,t){if(!Le)switch(e.tailMode){case"hidden":t=e.tail;for(var n=null;t!==null;)t.alternate!==null&&(n=t),t=t.sibling;n===null?e.tail=null:n.sibling=null;break;case"collapsed":n=e.tail;for(var r=null;n!==null;)n.alternate!==null&&(r=n),n=n.sibling;r===null?t||e.tail===null?e.tail=null:e.tail.sibling=null:r.sibling=null}}function et(e){var t=e.alternate!==null&&e.alternate.child===e.child,n=0,r=0;if(t)for(var i=e.child;i!==null;)n|=i.lanes|i.childLanes,r|=i.subtreeFlags&14680064,r|=i.flags&14680064,i.return=e,i=i.sibling;else for(i=e.child;i!==null;)n|=i.lanes|i.childLanes,r|=i.subtreeFlags,r|=i.flags,i.return=e,i=i.sibling;return e.subtreeFlags|=r,e.childLanes=n,t}function Pf(e,t,n){var r=t.pendingProps;switch(Il(t),t.tag){case 2:case 16:case 15:case 0:case 11:case 7:case 8:case 12:case 9:case 14:return et(t),null;case 1:return ct(t.type)&&fo(),et(t),null;case 3:return r=t.stateNode,Cr(),De(ut),De(Ze),Gl(),r.pendingContext&&(r.context=r.pendingContext,r.pendingContext=null),(e===null||e.child===null)&&(vo(t)?t.flags|=4:e===null||e.memoizedState.isDehydrated&&(t.flags&256)===0||(t.flags|=1024,bt!==null&&(Na(bt),bt=null))),ga(e,t),et(t),null;case 5:Yl(t);var i=qn(di.current);if(n=t.type,e!==null&&t.stateNode!=null)Gu(e,t,n,r,i),e.ref!==t.ref&&(t.flags|=512,t.flags|=2097152);else{if(!r){if(t.stateNode===null)throw Error(u(166));return et(t),null}if(e=qn(Qt.current),vo(t)){r=t.stateNode,n=t.type;var l=t.memoizedProps;switch(r[Ht]=t,r[li]=l,e=(t.mode&1)!==0,n){case"dialog":Ee("cancel",r),Ee("close",r);break;case"iframe":case"object":case"embed":Ee("load",r);break;case"video":case"audio":for(i=0;i<ri.length;i++)Ee(ri[i],r);break;case"source":Ee("error",r);break;case"img":case"image":case"link":Ee("error",r),Ee("load",r);break;case"details":Ee("toggle",r);break;case"input":Xe(r,l),Ee("invalid",r);break;case"select":r._wrapperState={wasMultiple:!!l.multiple},Ee("invalid",r);break;case"textarea":or(r,l),Ee("invalid",r)}Fi(n,l),i=null;for(var s in l)if(l.hasOwnProperty(s)){var d=l[s];s==="children"?typeof d=="string"?r.textContent!==d&&(l.suppressHydrationWarning!==!0&&so(r.textContent,d,e),i=["children",d]):typeof d=="number"&&r.textContent!==""+d&&(l.suppressHydrationWarning!==!0&&so(r.textContent,d,e),i=["children",""+d]):g.hasOwnProperty(s)&&d!=null&&s==="onScroll"&&Ee("scroll",r)}switch(n){case"input":lt(r),Gt(r,l,!0);break;case"textarea":lt(r),fn(r);break;case"select":case"option":break;default:typeof l.onClick=="function"&&(r.onclick=uo)}r=i,t.updateQueue=r,r!==null&&(t.flags|=4)}else{s=i.nodeType===9?i:i.ownerDocument,e==="http://www.w3.org/1999/xhtml"&&(e=ar(n)),e==="http://www.w3.org/1999/xhtml"?n==="script"?(e=s.createElement("div"),e.innerHTML="<script><\/script>",e=e.removeChild(e.firstChild)):typeof r.is=="string"?e=s.createElement(n,{is:r.is}):(e=s.createElement(n),n==="select"&&(s=e,r.multiple?s.multiple=!0:r.size&&(s.size=r.size))):e=s.createElementNS(e,n),e[Ht]=t,e[li]=r,qu(e,t,!1,!1),t.stateNode=e;e:{switch(s=Ar(n,r),n){case"dialog":Ee("cancel",e),Ee("close",e),i=r;break;case"iframe":case"object":case"embed":Ee("load",e),i=r;break;case"video":case"audio":for(i=0;i<ri.length;i++)Ee(ri[i],e);i=r;break;case"source":Ee("error",e),i=r;break;case"img":case"image":case"link":Ee("error",e),Ee("load",e),i=r;break;case"details":Ee("toggle",e),i=r;break;case"input":Xe(e,r),i=Rt(e,r),Ee("invalid",e);break;case"option":i=r;break;case"select":e._wrapperState={wasMultiple:!!r.multiple},i=$({},r,{value:void 0}),Ee("invalid",e);break;case"textarea":or(e,r),i=at(e,r),Ee("invalid",e);break;default:i=r}Fi(n,i),d=i;for(l in d)if(d.hasOwnProperty(l)){var p=d[l];l==="style"?Mi(e,p):l==="dangerouslySetInnerHTML"?(p=p?p.__html:void 0,p!=null&&An(e,p)):l==="children"?typeof p=="string"?(n!=="textarea"||p!=="")&&Zt(e,p):typeof p=="number"&&Zt(e,""+p):l!=="suppressContentEditableWarning"&&l!=="suppressHydrationWarning"&&l!=="autoFocus"&&(g.hasOwnProperty(l)?p!=null&&l==="onScroll"&&Ee("scroll",e):p!=null&&ze(e,l,p,s))}switch(n){case"input":lt(e),Gt(e,r,!1);break;case"textarea":lt(e),fn(e);break;case"option":r.value!=null&&e.setAttribute("value",""+ge(r.value));break;case"select":e.multiple=!!r.multiple,l=r.value,l!=null?gt(e,!!r.multiple,l,!1):r.defaultValue!=null&&gt(e,!!r.multiple,r.defaultValue,!0);break;default:typeof i.onClick=="function"&&(e.onclick=uo)}switch(n){case"button":case"input":case"select":case"textarea":r=!!r.autoFocus;break e;case"img":r=!0;break e;default:r=!1}}r&&(t.flags|=4)}t.ref!==null&&(t.flags|=512,t.flags|=2097152)}return et(t),null;case 6:if(e&&t.stateNode!=null)Xu(e,t,e.memoizedProps,r);else{if(typeof r!="string"&&t.stateNode===null)throw Error(u(166));if(n=qn(di.current),qn(Qt.current),vo(t)){if(r=t.stateNode,n=t.memoizedProps,r[Ht]=t,(l=r.nodeValue!==n)&&(e=wt,e!==null))switch(e.tag){case 3:so(r.nodeValue,n,(e.mode&1)!==0);break;case 5:e.memoizedProps.suppressHydrationWarning!==!0&&so(r.nodeValue,n,(e.mode&1)!==0)}l&&(t.flags|=4)}else r=(n.nodeType===9?n:n.ownerDocument).createTextNode(r),r[Ht]=t,t.stateNode=r}return et(t),null;case 13:if(De(Pe),r=t.memoizedState,e===null||e.memoizedState!==null&&e.memoizedState.dehydrated!==null){if(Le&&kt!==null&&(t.mode&1)!==0&&(t.flags&128)===0)eu(),_r(),t.flags|=98560,l=!1;else if(l=vo(t),r!==null&&r.dehydrated!==null){if(e===null){if(!l)throw Error(u(318));if(l=t.memoizedState,l=l!==null?l.dehydrated:null,!l)throw Error(u(317));l[Ht]=t}else _r(),(t.flags&128)===0&&(t.memoizedState=null),t.flags|=4;et(t),l=!1}else bt!==null&&(Na(bt),bt=null),l=!0;if(!l)return t.flags&65536?t:null}return(t.flags&128)!==0?(t.lanes=n,t):(r=r!==null,r!==(e!==null&&e.memoizedState!==null)&&r&&(t.child.flags|=8192,(t.mode&1)!==0&&(e===null||(Pe.current&1)!==0?be===0&&(be=3):Da())),t.updateQueue!==null&&(t.flags|=4),et(t),null);case 4:return Cr(),ga(e,t),e===null&&ii(t.stateNode.containerInfo),et(t),null;case 10:return Bl(t.type._context),et(t),null;case 17:return ct(t.type)&&fo(),et(t),null;case 19:if(De(Pe),l=t.memoizedState,l===null)return et(t),null;if(r=(t.flags&128)!==0,s=l.rendering,s===null)if(r)mi(l,!1);else{if(be!==0||e!==null&&(e.flags&128)!==0)for(e=t.child;e!==null;){if(s=_o(e),s!==null){for(t.flags|=128,mi(l,!1),r=s.updateQueue,r!==null&&(t.updateQueue=r,t.flags|=4),t.subtreeFlags=0,r=n,n=t.child;n!==null;)l=n,e=r,l.flags&=14680066,s=l.alternate,s===null?(l.childLanes=0,l.lanes=e,l.child=null,l.subtreeFlags=0,l.memoizedProps=null,l.memoizedState=null,l.updateQueue=null,l.dependencies=null,l.stateNode=null):(l.childLanes=s.childLanes,l.lanes=s.lanes,l.child=s.child,l.subtreeFlags=0,l.deletions=null,l.memoizedProps=s.memoizedProps,l.memoizedState=s.memoizedState,l.updateQueue=s.updateQueue,l.type=s.type,e=s.dependencies,l.dependencies=e===null?null:{lanes:e.lanes,firstContext:e.firstContext}),n=n.sibling;return Ne(Pe,Pe.current&1|2),t.child}e=e.sibling}l.tail!==null&&O()>Pr&&(t.flags|=128,r=!0,mi(l,!1),t.lanes=4194304)}else{if(!r)if(e=_o(s),e!==null){if(t.flags|=128,r=!0,n=e.updateQueue,n!==null&&(t.updateQueue=n,t.flags|=4),mi(l,!0),l.tail===null&&l.tailMode==="hidden"&&!s.alternate&&!Le)return et(t),null}else 2*O()-l.renderingStartTime>Pr&&n!==1073741824&&(t.flags|=128,r=!0,mi(l,!1),t.lanes=4194304);l.isBackwards?(s.sibling=t.child,t.child=s):(n=l.last,n!==null?n.sibling=s:t.child=s,l.last=s)}return l.tail!==null?(t=l.tail,l.rendering=t,l.tail=t.sibling,l.renderingStartTime=O(),t.sibling=null,n=Pe.current,Ne(Pe,r?n&1|2:n&1),t):(et(t),null);case 22:case 23:return Ea(),r=t.memoizedState!==null,e!==null&&e.memoizedState!==null!==r&&(t.flags|=8192),r&&(t.mode&1)!==0?(St&1073741824)!==0&&(et(t),t.subtreeFlags&6&&(t.flags|=8192)):et(t),null;case 24:return null;case 25:return null}throw Error(u(156,t.tag))}function Tf(e,t){switch(Il(t),t.tag){case 1:return ct(t.type)&&fo(),e=t.flags,e&65536?(t.flags=e&-65537|128,t):null;case 3:return Cr(),De(ut),De(Ze),Gl(),e=t.flags,(e&65536)!==0&&(e&128)===0?(t.flags=e&-65537|128,t):null;case 5:return Yl(t),null;case 13:if(De(Pe),e=t.memoizedState,e!==null&&e.dehydrated!==null){if(t.alternate===null)throw Error(u(340));_r()}return e=t.flags,e&65536?(t.flags=e&-65537|128,t):null;case 19:return De(Pe),null;case 4:return Cr(),null;case 10:return Bl(t.type._context),null;case 22:case 23:return Ea(),null;case 24:return null;default:return null}}var To=!1,tt=!1,Mf=typeof WeakSet=="function"?WeakSet:Set,V=null;function Dr(e,t){var n=e.ref;if(n!==null)if(typeof n=="function")try{n(null)}catch(r){Fe(e,t,r)}else n.current=null}function ma(e,t,n){try{n()}catch(r){Fe(e,t,r)}}var Zu=!1;function Ff(e,t){if(El=Xi,e=Ls(),wl(e)){if("selectionStart"in e)var n={start:e.selectionStart,end:e.selectionEnd};else e:{n=(n=e.ownerDocument)&&n.defaultView||window;var r=n.getSelection&&n.getSelection();if(r&&r.rangeCount!==0){n=r.anchorNode;var i=r.anchorOffset,l=r.focusNode;r=r.focusOffset;try{n.nodeType,l.nodeType}catch{n=null;break e}var s=0,d=-1,p=-1,S=0,C=0,L=e,z=null;t:for(;;){for(var b;L!==n||i!==0&&L.nodeType!==3||(d=s+i),L!==l||r!==0&&L.nodeType!==3||(p=s+r),L.nodeType===3&&(s+=L.nodeValue.length),(b=L.firstChild)!==null;)z=L,L=b;for(;;){if(L===e)break t;if(z===n&&++S===i&&(d=s),z===l&&++C===r&&(p=s),(b=L.nextSibling)!==null)break;L=z,z=L.parentNode}L=b}n=d===-1||p===-1?null:{start:d,end:p}}else n=null}n=n||{start:0,end:0}}else n=null;for(Dl={focusedElem:e,selectionRange:n},Xi=!1,V=t;V!==null;)if(t=V,e=t.child,(t.subtreeFlags&1028)!==0&&e!==null)e.return=t,V=e;else for(;V!==null;){t=V;try{var W=t.alternate;if((t.flags&1024)!==0)switch(t.tag){case 0:case 11:case 15:break;case 1:if(W!==null){var Q=W.memoizedProps,Oe=W.memoizedState,y=t.stateNode,m=y.getSnapshotBeforeUpdate(t.elementType===t.type?Q:Ut(t.type,Q),Oe);y.__reactInternalSnapshotBeforeUpdate=m}break;case 3:var w=t.stateNode.containerInfo;w.nodeType===1?w.textContent="":w.nodeType===9&&w.documentElement&&w.removeChild(w.documentElement);break;case 5:case 6:case 4:case 17:break;default:throw Error(u(163))}}catch(P){Fe(t,t.return,P)}if(e=t.sibling,e!==null){e.return=t.return,V=e;break}V=t.return}return W=Zu,Zu=!1,W}function vi(e,t,n){var r=t.updateQueue;if(r=r!==null?r.lastEffect:null,r!==null){var i=r=r.next;do{if((i.tag&e)===e){var l=i.destroy;i.destroy=void 0,l!==void 0&&ma(t,n,l)}i=i.next}while(i!==r)}}function Mo(e,t){if(t=t.updateQueue,t=t!==null?t.lastEffect:null,t!==null){var n=t=t.next;do{if((n.tag&e)===e){var r=n.create;n.destroy=r()}n=n.next}while(n!==t)}}function va(e){var t=e.ref;if(t!==null){var n=e.stateNode;switch(e.tag){case 5:e=n;break;default:e=n}typeof t=="function"?t(e):t.current=e}}function Ju(e){var t=e.alternate;t!==null&&(e.alternate=null,Ju(t)),e.child=null,e.deletions=null,e.sibling=null,e.tag===5&&(t=e.stateNode,t!==null&&(delete t[Ht],delete t[li],delete t[Ml],delete t[mf],delete t[vf])),e.stateNode=null,e.return=null,e.dependencies=null,e.memoizedProps=null,e.memoizedState=null,e.pendingProps=null,e.stateNode=null,e.updateQueue=null}function ec(e){return e.tag===5||e.tag===3||e.tag===4}function tc(e){e:for(;;){for(;e.sibling===null;){if(e.return===null||ec(e.return))return null;e=e.return}for(e.sibling.return=e.return,e=e.sibling;e.tag!==5&&e.tag!==6&&e.tag!==18;){if(e.flags&2||e.child===null||e.tag===4)continue e;e.child.return=e,e=e.child}if(!(e.flags&2))return e.stateNode}}function ya(e,t,n){var r=e.tag;if(r===5||r===6)e=e.stateNode,t?n.nodeType===8?n.parentNode.insertBefore(e,t):n.insertBefore(e,t):(n.nodeType===8?(t=n.parentNode,t.insertBefore(e,n)):(t=n,t.appendChild(e)),n=n._reactRootContainer,n!=null||t.onclick!==null||(t.onclick=uo));else if(r!==4&&(e=e.child,e!==null))for(ya(e,t,n),e=e.sibling;e!==null;)ya(e,t,n),e=e.sibling}function xa(e,t,n){var r=e.tag;if(r===5||r===6)e=e.stateNode,t?n.insertBefore(e,t):n.appendChild(e);else if(r!==4&&(e=e.child,e!==null))for(xa(e,t,n),e=e.sibling;e!==null;)xa(e,t,n),e=e.sibling}var Qe=null,$t=!1;function Nn(e,t,n){for(n=n.child;n!==null;)nc(e,t,n),n=n.sibling}function nc(e,t,n){if(R&&typeof R.onCommitFiberUnmount=="function")try{R.onCommitFiberUnmount(Bn,n)}catch{}switch(n.tag){case 5:tt||Dr(n,t);case 6:var r=Qe,i=$t;Qe=null,Nn(e,t,n),Qe=r,$t=i,Qe!==null&&($t?(e=Qe,n=n.stateNode,e.nodeType===8?e.parentNode.removeChild(n):e.removeChild(n)):Qe.removeChild(n.stateNode));break;case 18:Qe!==null&&($t?(e=Qe,n=n.stateNode,e.nodeType===8?Tl(e.parentNode,n):e.nodeType===1&&Tl(e,n),qr(e)):Tl(Qe,n.stateNode));break;case 4:r=Qe,i=$t,Qe=n.stateNode.containerInfo,$t=!0,Nn(e,t,n),Qe=r,$t=i;break;case 0:case 11:case 14:case 15:if(!tt&&(r=n.updateQueue,r!==null&&(r=r.lastEffect,r!==null))){i=r=r.next;do{var l=i,s=l.destroy;l=l.tag,s!==void 0&&((l&2)!==0||(l&4)!==0)&&ma(n,t,s),i=i.next}while(i!==r)}Nn(e,t,n);break;case 1:if(!tt&&(Dr(n,t),r=n.stateNode,typeof r.componentWillUnmount=="function"))try{r.props=n.memoizedProps,r.state=n.memoizedState,r.componentWillUnmount()}catch(d){Fe(n,t,d)}Nn(e,t,n);break;case 21:Nn(e,t,n);break;case 22:n.mode&1?(tt=(r=tt)||n.memoizedState!==null,Nn(e,t,n),tt=r):Nn(e,t,n);break;default:Nn(e,t,n)}}function rc(e){var t=e.updateQueue;if(t!==null){e.updateQueue=null;var n=e.stateNode;n===null&&(n=e.stateNode=new Mf),t.forEach(function(r){var i=Bf.bind(null,e,r);n.has(r)||(n.add(r),r.then(i,i))})}}function Vt(e,t){var n=t.deletions;if(n!==null)for(var r=0;r<n.length;r++){var i=n[r];try{var l=e,s=t,d=s;e:for(;d!==null;){switch(d.tag){case 5:Qe=d.stateNode,$t=!1;break e;case 3:Qe=d.stateNode.containerInfo,$t=!0;break e;case 4:Qe=d.stateNode.containerInfo,$t=!0;break e}d=d.return}if(Qe===null)throw Error(u(160));nc(l,s,i),Qe=null,$t=!1;var p=i.alternate;p!==null&&(p.return=null),i.return=null}catch(S){Fe(i,t,S)}}if(t.subtreeFlags&12854)for(t=t.child;t!==null;)ic(t,e),t=t.sibling}function ic(e,t){var n=e.alternate,r=e.flags;switch(e.tag){case 0:case 11:case 14:case 15:if(Vt(t,e),Yt(e),r&4){try{vi(3,e,e.return),Mo(3,e)}catch(Q){Fe(e,e.return,Q)}try{vi(5,e,e.return)}catch(Q){Fe(e,e.return,Q)}}break;case 1:Vt(t,e),Yt(e),r&512&&n!==null&&Dr(n,n.return);break;case 5:if(Vt(t,e),Yt(e),r&512&&n!==null&&Dr(n,n.return),e.flags&32){var i=e.stateNode;try{Zt(i,"")}catch(Q){Fe(e,e.return,Q)}}if(r&4&&(i=e.stateNode,i!=null)){var l=e.memoizedProps,s=n!==null?n.memoizedProps:l,d=e.type,p=e.updateQueue;if(e.updateQueue=null,p!==null)try{d==="input"&&l.type==="radio"&&l.name!=null&&Ot(i,l),Ar(d,s);var S=Ar(d,l);for(s=0;s<p.length;s+=2){var C=p[s],L=p[s+1];C==="style"?Mi(i,L):C==="dangerouslySetInnerHTML"?An(i,L):C==="children"?Zt(i,L):ze(i,C,L,S)}switch(d){case"input":jt(i,l);break;case"textarea":lr(i,l);break;case"select":var z=i._wrapperState.wasMultiple;i._wrapperState.wasMultiple=!!l.multiple;var b=l.value;b!=null?gt(i,!!l.multiple,b,!1):z!==!!l.multiple&&(l.defaultValue!=null?gt(i,!!l.multiple,l.defaultValue,!0):gt(i,!!l.multiple,l.multiple?[]:"",!1))}i[li]=l}catch(Q){Fe(e,e.return,Q)}}break;case 6:if(Vt(t,e),Yt(e),r&4){if(e.stateNode===null)throw Error(u(162));i=e.stateNode,l=e.memoizedProps;try{i.nodeValue=l}catch(Q){Fe(e,e.return,Q)}}break;case 3:if(Vt(t,e),Yt(e),r&4&&n!==null&&n.memoizedState.isDehydrated)try{qr(t.containerInfo)}catch(Q){Fe(e,e.return,Q)}break;case 4:Vt(t,e),Yt(e);break;case 13:Vt(t,e),Yt(e),i=e.child,i.flags&8192&&(l=i.memoizedState!==null,i.stateNode.isHidden=l,!l||i.alternate!==null&&i.alternate.memoizedState!==null||(Sa=O())),r&4&&rc(e);break;case 22:if(C=n!==null&&n.memoizedState!==null,e.mode&1?(tt=(S=tt)||C,Vt(t,e),tt=S):Vt(t,e),Yt(e),r&8192){if(S=e.memoizedState!==null,(e.stateNode.isHidden=S)&&!C&&(e.mode&1)!==0)for(V=e,C=e.child;C!==null;){for(L=V=C;V!==null;){switch(z=V,b=z.child,z.tag){case 0:case 11:case 14:case 15:vi(4,z,z.return);break;case 1:Dr(z,z.return);var W=z.stateNode;if(typeof W.componentWillUnmount=="function"){r=z,n=z.return;try{t=r,W.props=t.memoizedProps,W.state=t.memoizedState,W.componentWillUnmount()}catch(Q){Fe(r,n,Q)}}break;case 5:Dr(z,z.return);break;case 22:if(z.memoizedState!==null){ac(L);continue}}b!==null?(b.return=z,V=b):ac(L)}C=C.sibling}e:for(C=null,L=e;;){if(L.tag===5){if(C===null){C=L;try{i=L.stateNode,S?(l=i.style,typeof l.setProperty=="function"?l.setProperty("display","none","important"):l.display="none"):(d=L.stateNode,p=L.memoizedProps.style,s=p!=null&&p.hasOwnProperty("display")?p.display:null,d.style.display=Ir("display",s))}catch(Q){Fe(e,e.return,Q)}}}else if(L.tag===6){if(C===null)try{L.stateNode.nodeValue=S?"":L.memoizedProps}catch(Q){Fe(e,e.return,Q)}}else if((L.tag!==22&&L.tag!==23||L.memoizedState===null||L===e)&&L.child!==null){L.child.return=L,L=L.child;continue}if(L===e)break e;for(;L.sibling===null;){if(L.return===null||L.return===e)break e;C===L&&(C=null),L=L.return}C===L&&(C=null),L.sibling.return=L.return,L=L.sibling}}break;case 19:Vt(t,e),Yt(e),r&4&&rc(e);break;case 21:break;default:Vt(t,e),Yt(e)}}function Yt(e){var t=e.flags;if(t&2){try{e:{for(var n=e.return;n!==null;){if(ec(n)){var r=n;break e}n=n.return}throw Error(u(160))}switch(r.tag){case 5:var i=r.stateNode;r.flags&32&&(Zt(i,""),r.flags&=-33);var l=tc(e);xa(e,l,i);break;case 3:case 4:var s=r.stateNode.containerInfo,d=tc(e);ya(e,d,s);break;default:throw Error(u(161))}}catch(p){Fe(e,e.return,p)}e.flags&=-3}t&4096&&(e.flags&=-4097)}function Rf(e,t,n){V=e,oc(e)}function oc(e,t,n){for(var r=(e.mode&1)!==0;V!==null;){var i=V,l=i.child;if(i.tag===22&&r){var s=i.memoizedState!==null||To;if(!s){var d=i.alternate,p=d!==null&&d.memoizedState!==null||tt;d=To;var S=tt;if(To=s,(tt=p)&&!S)for(V=i;V!==null;)s=V,p=s.child,s.tag===22&&s.memoizedState!==null?sc(i):p!==null?(p.return=s,V=p):sc(i);for(;l!==null;)V=l,oc(l),l=l.sibling;V=i,To=d,tt=S}lc(e)}else(i.subtreeFlags&8772)!==0&&l!==null?(l.return=i,V=l):lc(e)}}function lc(e){for(;V!==null;){var t=V;if((t.flags&8772)!==0){var n=t.alternate;try{if((t.flags&8772)!==0)switch(t.tag){case 0:case 11:case 15:tt||Mo(5,t);break;case 1:var r=t.stateNode;if(t.flags&4&&!tt)if(n===null)r.componentDidMount();else{var i=t.elementType===t.type?n.memoizedProps:Ut(t.type,n.memoizedProps);r.componentDidUpdate(i,n.memoizedState,r.__reactInternalSnapshotBeforeUpdate)}var l=t.updateQueue;l!==null&&au(t,l,r);break;case 3:var s=t.updateQueue;if(s!==null){if(n=null,t.child!==null)switch(t.child.tag){case 5:n=t.child.stateNode;break;case 1:n=t.child.stateNode}au(t,s,n)}break;case 5:var d=t.stateNode;if(n===null&&t.flags&4){n=d;var p=t.memoizedProps;switch(t.type){case"button":case"input":case"select":case"textarea":p.autoFocus&&n.focus();break;case"img":p.src&&(n.src=p.src)}}break;case 6:break;case 4:break;case 12:break;case 13:if(t.memoizedState===null){var S=t.alternate;if(S!==null){var C=S.memoizedState;if(C!==null){var L=C.dehydrated;L!==null&&qr(L)}}}break;case 19:case 17:case 21:case 22:case 23:case 25:break;default:throw Error(u(163))}tt||t.flags&512&&va(t)}catch(z){Fe(t,t.return,z)}}if(t===e){V=null;break}if(n=t.sibling,n!==null){n.return=t.return,V=n;break}V=t.return}}function ac(e){for(;V!==null;){var t=V;if(t===e){V=null;break}var n=t.sibling;if(n!==null){n.return=t.return,V=n;break}V=t.return}}function sc(e){for(;V!==null;){var t=V;try{switch(t.tag){case 0:case 11:case 15:var n=t.return;try{Mo(4,t)}catch(p){Fe(t,n,p)}break;case 1:var r=t.stateNode;if(typeof r.componentDidMount=="function"){var i=t.return;try{r.componentDidMount()}catch(p){Fe(t,i,p)}}var l=t.return;try{va(t)}catch(p){Fe(t,l,p)}break;case 5:var s=t.return;try{va(t)}catch(p){Fe(t,s,p)}}}catch(p){Fe(t,t.return,p)}if(t===e){V=null;break}var d=t.sibling;if(d!==null){d.return=t.return,V=d;break}V=t.return}}var Of=Math.ceil,Fo=pe.ReactCurrentDispatcher,wa=pe.ReactCurrentOwner,Mt=pe.ReactCurrentBatchConfig,fe=0,Be=null,Ie=null,Ke=0,St=0,Lr=kn(0),be=0,yi=null,Xn=0,Ro=0,ka=0,xi=null,ft=null,Sa=0,Pr=1/0,cn=null,Oo=!1,_a=null,Cn=null,Io=!1,En=null,Ao=0,wi=0,ja=null,bo=-1,Uo=0;function ot(){return(fe&6)!==0?O():bo!==-1?bo:bo=O()}function Dn(e){return(e.mode&1)===0?1:(fe&2)!==0&&Ke!==0?Ke&-Ke:xf.transition!==null?(Uo===0&&(Uo=ts()),Uo):(e=we,e!==0||(e=window.event,e=e===void 0?16:cs(e.type)),e)}function Bt(e,t,n,r){if(50<wi)throw wi=0,ja=null,Error(u(185));Wr(e,n,r),((fe&2)===0||e!==Be)&&(e===Be&&((fe&2)===0&&(Ro|=n),be===4&&Ln(e,Ke)),pt(e,r),n===1&&fe===0&&(t.mode&1)===0&&(Pr=O()+500,ho&&_n()))}function pt(e,t){var n=e.callbackNode;yd(e,t);var r=Yi(e,e===Be?Ke:0);if(r===0)n!==null&&h(n),e.callbackNode=null,e.callbackPriority=0;else if(t=r&-r,e.callbackPriority!==t){if(n!=null&&h(n),t===1)e.tag===0?yf(cc.bind(null,e)):qs(cc.bind(null,e)),hf(function(){(fe&6)===0&&_n()}),n=null;else{switch(ns(r)){case 1:n=Re;break;case 4:n=yt;break;case 16:n=Ce;break;case 536870912:n=tn;break;default:n=Ce}n=yc(n,uc.bind(null,e))}e.callbackPriority=t,e.callbackNode=n}}function uc(e,t){if(bo=-1,Uo=0,(fe&6)!==0)throw Error(u(327));var n=e.callbackNode;if(Tr()&&e.callbackNode!==n)return null;var r=Yi(e,e===Be?Ke:0);if(r===0)return null;if((r&30)!==0||(r&e.expiredLanes)!==0||t)t=$o(e,r);else{t=r;var i=fe;fe|=2;var l=fc();(Be!==e||Ke!==t)&&(cn=null,Pr=O()+500,Jn(e,t));do try{bf();break}catch(d){dc(e,d)}while(!0);Vl(),Fo.current=l,fe=i,Ie!==null?t=0:(Be=null,Ke=0,t=be)}if(t!==0){if(t===2&&(i=il(e),i!==0&&(r=i,t=za(e,i))),t===1)throw n=yi,Jn(e,0),Ln(e,r),pt(e,O()),n;if(t===6)Ln(e,r);else{if(i=e.current.alternate,(r&30)===0&&!If(i)&&(t=$o(e,r),t===2&&(l=il(e),l!==0&&(r=l,t=za(e,l))),t===1))throw n=yi,Jn(e,0),Ln(e,r),pt(e,O()),n;switch(e.finishedWork=i,e.finishedLanes=r,t){case 0:case 1:throw Error(u(345));case 2:er(e,ft,cn);break;case 3:if(Ln(e,r),(r&130023424)===r&&(t=Sa+500-O(),10<t)){if(Yi(e,0)!==0)break;if(i=e.suspendedLanes,(i&r)!==r){ot(),e.pingedLanes|=e.suspendedLanes&i;break}e.timeoutHandle=Pl(er.bind(null,e,ft,cn),t);break}er(e,ft,cn);break;case 4:if(Ln(e,r),(r&4194240)===r)break;for(t=e.eventTimes,i=-1;0<r;){var s=31-st(r);l=1<<s,s=t[s],s>i&&(i=s),r&=~l}if(r=i,r=O()-r,r=(120>r?120:480>r?480:1080>r?1080:1920>r?1920:3e3>r?3e3:4320>r?4320:1960*Of(r/1960))-r,10<r){e.timeoutHandle=Pl(er.bind(null,e,ft,cn),r);break}er(e,ft,cn);break;case 5:er(e,ft,cn);break;default:throw Error(u(329))}}}return pt(e,O()),e.callbackNode===n?uc.bind(null,e):null}function za(e,t){var n=xi;return e.current.memoizedState.isDehydrated&&(Jn(e,t).flags|=256),e=$o(e,t),e!==2&&(t=ft,ft=n,t!==null&&Na(t)),e}function Na(e){ft===null?ft=e:ft.push.apply(ft,e)}function If(e){for(var t=e;;){if(t.flags&16384){var n=t.updateQueue;if(n!==null&&(n=n.stores,n!==null))for(var r=0;r<n.length;r++){var i=n[r],l=i.getSnapshot;i=i.value;try{if(!At(l(),i))return!1}catch{return!1}}}if(n=t.child,t.subtreeFlags&16384&&n!==null)n.return=t,t=n;else{if(t===e)break;for(;t.sibling===null;){if(t.return===null||t.return===e)return!0;t=t.return}t.sibling.return=t.return,t=t.sibling}}return!0}function Ln(e,t){for(t&=~ka,t&=~Ro,e.suspendedLanes|=t,e.pingedLanes&=~t,e=e.expirationTimes;0<t;){var n=31-st(t),r=1<<n;e[n]=-1,t&=~r}}function cc(e){if((fe&6)!==0)throw Error(u(327));Tr();var t=Yi(e,0);if((t&1)===0)return pt(e,O()),null;var n=$o(e,t);if(e.tag!==0&&n===2){var r=il(e);r!==0&&(t=r,n=za(e,r))}if(n===1)throw n=yi,Jn(e,0),Ln(e,t),pt(e,O()),n;if(n===6)throw Error(u(345));return e.finishedWork=e.current.alternate,e.finishedLanes=t,er(e,ft,cn),pt(e,O()),null}function Ca(e,t){var n=fe;fe|=1;try{return e(t)}finally{fe=n,fe===0&&(Pr=O()+500,ho&&_n())}}function Zn(e){En!==null&&En.tag===0&&(fe&6)===0&&Tr();var t=fe;fe|=1;var n=Mt.transition,r=we;try{if(Mt.transition=null,we=1,e)return e()}finally{we=r,Mt.transition=n,fe=t,(fe&6)===0&&_n()}}function Ea(){St=Lr.current,De(Lr)}function Jn(e,t){e.finishedWork=null,e.finishedLanes=0;var n=e.timeoutHandle;if(n!==-1&&(e.timeoutHandle=-1,pf(n)),Ie!==null)for(n=Ie.return;n!==null;){var r=n;switch(Il(r),r.tag){case 1:r=r.type.childContextTypes,r!=null&&fo();break;case 3:Cr(),De(ut),De(Ze),Gl();break;case 5:Yl(r);break;case 4:Cr();break;case 13:De(Pe);break;case 19:De(Pe);break;case 10:Bl(r.type._context);break;case 22:case 23:Ea()}n=n.return}if(Be=e,Ie=e=Pn(e.current,null),Ke=St=t,be=0,yi=null,ka=Ro=Xn=0,ft=xi=null,Yn!==null){for(t=0;t<Yn.length;t++)if(n=Yn[t],r=n.interleaved,r!==null){n.interleaved=null;var i=r.next,l=n.pending;if(l!==null){var s=l.next;l.next=i,r.next=s}n.pending=r}Yn=null}return e}function dc(e,t){do{var n=Ie;try{if(Vl(),jo.current=Eo,zo){for(var r=Te.memoizedState;r!==null;){var i=r.queue;i!==null&&(i.pending=null),r=r.next}zo=!1}if(Gn=0,Ve=Ae=Te=null,fi=!1,pi=0,wa.current=null,n===null||n.return===null){be=1,yi=t,Ie=null;break}e:{var l=e,s=n.return,d=n,p=t;if(t=Ke,d.flags|=32768,p!==null&&typeof p=="object"&&typeof p.then=="function"){var S=p,C=d,L=C.tag;if((C.mode&1)===0&&(L===0||L===11||L===15)){var z=C.alternate;z?(C.updateQueue=z.updateQueue,C.memoizedState=z.memoizedState,C.lanes=z.lanes):(C.updateQueue=null,C.memoizedState=null)}var b=Ou(s);if(b!==null){b.flags&=-257,Iu(b,s,d,l,t),b.mode&1&&Ru(l,S,t),t=b,p=S;var W=t.updateQueue;if(W===null){var Q=new Set;Q.add(p),t.updateQueue=Q}else W.add(p);break e}else{if((t&1)===0){Ru(l,S,t),Da();break e}p=Error(u(426))}}else if(Le&&d.mode&1){var Oe=Ou(s);if(Oe!==null){(Oe.flags&65536)===0&&(Oe.flags|=256),Iu(Oe,s,d,l,t),Ul(Er(p,d));break e}}l=p=Er(p,d),be!==4&&(be=2),xi===null?xi=[l]:xi.push(l),l=s;do{switch(l.tag){case 3:l.flags|=65536,t&=-t,l.lanes|=t;var y=Mu(l,p,t);lu(l,y);break e;case 1:d=p;var m=l.type,w=l.stateNode;if((l.flags&128)===0&&(typeof m.getDerivedStateFromError=="function"||w!==null&&typeof w.componentDidCatch=="function"&&(Cn===null||!Cn.has(w)))){l.flags|=65536,t&=-t,l.lanes|=t;var P=Fu(l,d,t);lu(l,P);break e}}l=l.return}while(l!==null)}hc(n)}catch(Y){t=Y,Ie===n&&n!==null&&(Ie=n=n.return);continue}break}while(!0)}function fc(){var e=Fo.current;return Fo.current=Eo,e===null?Eo:e}function Da(){(be===0||be===3||be===2)&&(be=4),Be===null||(Xn&268435455)===0&&(Ro&268435455)===0||Ln(Be,Ke)}function $o(e,t){var n=fe;fe|=2;var r=fc();(Be!==e||Ke!==t)&&(cn=null,Jn(e,t));do try{Af();break}catch(i){dc(e,i)}while(!0);if(Vl(),fe=n,Fo.current=r,Ie!==null)throw Error(u(261));return Be=null,Ke=0,be}function Af(){for(;Ie!==null;)pc(Ie)}function bf(){for(;Ie!==null&&!D();)pc(Ie)}function pc(e){var t=vc(e.alternate,e,St);e.memoizedProps=e.pendingProps,t===null?hc(e):Ie=t,wa.current=null}function hc(e){var t=e;do{var n=t.alternate;if(e=t.return,(t.flags&32768)===0){if(n=Pf(n,t,St),n!==null){Ie=n;return}}else{if(n=Tf(n,t),n!==null){n.flags&=32767,Ie=n;return}if(e!==null)e.flags|=32768,e.subtreeFlags=0,e.deletions=null;else{be=6,Ie=null;return}}if(t=t.sibling,t!==null){Ie=t;return}Ie=t=e}while(t!==null);be===0&&(be=5)}function er(e,t,n){var r=we,i=Mt.transition;try{Mt.transition=null,we=1,Uf(e,t,n,r)}finally{Mt.transition=i,we=r}return null}function Uf(e,t,n,r){do Tr();while(En!==null);if((fe&6)!==0)throw Error(u(327));n=e.finishedWork;var i=e.finishedLanes;if(n===null)return null;if(e.finishedWork=null,e.finishedLanes=0,n===e.current)throw Error(u(177));e.callbackNode=null,e.callbackPriority=0;var l=n.lanes|n.childLanes;if(xd(e,l),e===Be&&(Ie=Be=null,Ke=0),(n.subtreeFlags&2064)===0&&(n.flags&2064)===0||Io||(Io=!0,yc(Ce,function(){return Tr(),null})),l=(n.flags&15990)!==0,(n.subtreeFlags&15990)!==0||l){l=Mt.transition,Mt.transition=null;var s=we;we=1;var d=fe;fe|=4,wa.current=null,Ff(e,n),ic(n,e),lf(Dl),Xi=!!El,Dl=El=null,e.current=n,Rf(n),I(),fe=d,we=s,Mt.transition=l}else e.current=n;if(Io&&(Io=!1,En=e,Ao=i),l=e.pendingLanes,l===0&&(Cn=null),rt(n.stateNode),pt(e,O()),t!==null)for(r=e.onRecoverableError,n=0;n<t.length;n++)i=t[n],r(i.value,{componentStack:i.stack,digest:i.digest});if(Oo)throw Oo=!1,e=_a,_a=null,e;return(Ao&1)!==0&&e.tag!==0&&Tr(),l=e.pendingLanes,(l&1)!==0?e===ja?wi++:(wi=0,ja=e):wi=0,_n(),null}function Tr(){if(En!==null){var e=ns(Ao),t=Mt.transition,n=we;try{if(Mt.transition=null,we=16>e?16:e,En===null)var r=!1;else{if(e=En,En=null,Ao=0,(fe&6)!==0)throw Error(u(331));var i=fe;for(fe|=4,V=e.current;V!==null;){var l=V,s=l.child;if((V.flags&16)!==0){var d=l.deletions;if(d!==null){for(var p=0;p<d.length;p++){var S=d[p];for(V=S;V!==null;){var C=V;switch(C.tag){case 0:case 11:case 15:vi(8,C,l)}var L=C.child;if(L!==null)L.return=C,V=L;else for(;V!==null;){C=V;var z=C.sibling,b=C.return;if(Ju(C),C===S){V=null;break}if(z!==null){z.return=b,V=z;break}V=b}}}var W=l.alternate;if(W!==null){var Q=W.child;if(Q!==null){W.child=null;do{var Oe=Q.sibling;Q.sibling=null,Q=Oe}while(Q!==null)}}V=l}}if((l.subtreeFlags&2064)!==0&&s!==null)s.return=l,V=s;else e:for(;V!==null;){if(l=V,(l.flags&2048)!==0)switch(l.tag){case 0:case 11:case 15:vi(9,l,l.return)}var y=l.sibling;if(y!==null){y.return=l.return,V=y;break e}V=l.return}}var m=e.current;for(V=m;V!==null;){s=V;var w=s.child;if((s.subtreeFlags&2064)!==0&&w!==null)w.return=s,V=w;else e:for(s=m;V!==null;){if(d=V,(d.flags&2048)!==0)try{switch(d.tag){case 0:case 11:case 15:Mo(9,d)}}catch(Y){Fe(d,d.return,Y)}if(d===s){V=null;break e}var P=d.sibling;if(P!==null){P.return=d.return,V=P;break e}V=d.return}}if(fe=i,_n(),R&&typeof R.onPostCommitFiberRoot=="function")try{R.onPostCommitFiberRoot(Bn,e)}catch{}r=!0}return r}finally{we=n,Mt.transition=t}}return!1}function gc(e,t,n){t=Er(n,t),t=Mu(e,t,1),e=zn(e,t,1),t=ot(),e!==null&&(Wr(e,1,t),pt(e,t))}function Fe(e,t,n){if(e.tag===3)gc(e,e,n);else for(;t!==null;){if(t.tag===3){gc(t,e,n);break}else if(t.tag===1){var r=t.stateNode;if(typeof t.type.getDerivedStateFromError=="function"||typeof r.componentDidCatch=="function"&&(Cn===null||!Cn.has(r))){e=Er(n,e),e=Fu(t,e,1),t=zn(t,e,1),e=ot(),t!==null&&(Wr(t,1,e),pt(t,e));break}}t=t.return}}function $f(e,t,n){var r=e.pingCache;r!==null&&r.delete(t),t=ot(),e.pingedLanes|=e.suspendedLanes&n,Be===e&&(Ke&n)===n&&(be===4||be===3&&(Ke&130023424)===Ke&&500>O()-Sa?Jn(e,0):ka|=n),pt(e,t)}function mc(e,t){t===0&&((e.mode&1)===0?t=1:(t=Ki,Ki<<=1,(Ki&130023424)===0&&(Ki=4194304)));var n=ot();e=an(e,t),e!==null&&(Wr(e,t,n),pt(e,n))}function Vf(e){var t=e.memoizedState,n=0;t!==null&&(n=t.retryLane),mc(e,n)}function Bf(e,t){var n=0;switch(e.tag){case 13:var r=e.stateNode,i=e.memoizedState;i!==null&&(n=i.retryLane);break;case 19:r=e.stateNode;break;default:throw Error(u(314))}r!==null&&r.delete(t),mc(e,n)}var vc;vc=function(e,t,n){if(e!==null)if(e.memoizedProps!==t.pendingProps||ut.current)dt=!0;else{if((e.lanes&n)===0&&(t.flags&128)===0)return dt=!1,Lf(e,t,n);dt=(e.flags&131072)!==0}else dt=!1,Le&&(t.flags&1048576)!==0&&Gs(t,mo,t.index);switch(t.lanes=0,t.tag){case 2:var r=t.type;Po(e,t),e=t.pendingProps;var i=wr(t,Ze.current);Nr(t,n),i=Jl(null,t,r,e,i,n);var l=ea();return t.flags|=1,typeof i=="object"&&i!==null&&typeof i.render=="function"&&i.$$typeof===void 0?(t.tag=1,t.memoizedState=null,t.updateQueue=null,ct(r)?(l=!0,po(t)):l=!1,t.memoizedState=i.state!==null&&i.state!==void 0?i.state:null,Ql(t),i.updater=Do,t.stateNode=i,i._reactInternals=t,la(t,r,e,n),t=ca(null,t,r,!0,l,n)):(t.tag=0,Le&&l&&Ol(t),it(null,t,i,n),t=t.child),t;case 16:r=t.elementType;e:{switch(Po(e,t),e=t.pendingProps,i=r._init,r=i(r._payload),t.type=r,i=t.tag=Hf(r),e=Ut(r,e),i){case 0:t=ua(null,t,r,e,n);break e;case 1:t=Bu(null,t,r,e,n);break e;case 11:t=Au(null,t,r,e,n);break e;case 14:t=bu(null,t,r,Ut(r.type,e),n);break e}throw Error(u(306,r,""))}return t;case 0:return r=t.type,i=t.pendingProps,i=t.elementType===r?i:Ut(r,i),ua(e,t,r,i,n);case 1:return r=t.type,i=t.pendingProps,i=t.elementType===r?i:Ut(r,i),Bu(e,t,r,i,n);case 3:e:{if(Wu(t),e===null)throw Error(u(387));r=t.pendingProps,l=t.memoizedState,i=l.element,ou(e,t),So(t,r,null,n);var s=t.memoizedState;if(r=s.element,l.isDehydrated)if(l={element:r,isDehydrated:!1,cache:s.cache,pendingSuspenseBoundaries:s.pendingSuspenseBoundaries,transitions:s.transitions},t.updateQueue.baseState=l,t.memoizedState=l,t.flags&256){i=Er(Error(u(423)),t),t=Hu(e,t,r,n,i);break e}else if(r!==i){i=Er(Error(u(424)),t),t=Hu(e,t,r,n,i);break e}else for(kt=wn(t.stateNode.containerInfo.firstChild),wt=t,Le=!0,bt=null,n=ru(t,null,r,n),t.child=n;n;)n.flags=n.flags&-3|4096,n=n.sibling;else{if(_r(),r===i){t=un(e,t,n);break e}it(e,t,r,n)}t=t.child}return t;case 5:return su(t),e===null&&bl(t),r=t.type,i=t.pendingProps,l=e!==null?e.memoizedProps:null,s=i.children,Ll(r,i)?s=null:l!==null&&Ll(r,l)&&(t.flags|=32),Vu(e,t),it(e,t,s,n),t.child;case 6:return e===null&&bl(t),null;case 13:return Qu(e,t,n);case 4:return Kl(t,t.stateNode.containerInfo),r=t.pendingProps,e===null?t.child=jr(t,null,r,n):it(e,t,r,n),t.child;case 11:return r=t.type,i=t.pendingProps,i=t.elementType===r?i:Ut(r,i),Au(e,t,r,i,n);case 7:return it(e,t,t.pendingProps,n),t.child;case 8:return it(e,t,t.pendingProps.children,n),t.child;case 12:return it(e,t,t.pendingProps.children,n),t.child;case 10:e:{if(r=t.type._context,i=t.pendingProps,l=t.memoizedProps,s=i.value,Ne(xo,r._currentValue),r._currentValue=s,l!==null)if(At(l.value,s)){if(l.children===i.children&&!ut.current){t=un(e,t,n);break e}}else for(l=t.child,l!==null&&(l.return=t);l!==null;){var d=l.dependencies;if(d!==null){s=l.child;for(var p=d.firstContext;p!==null;){if(p.context===r){if(l.tag===1){p=sn(-1,n&-n),p.tag=2;var S=l.updateQueue;if(S!==null){S=S.shared;var C=S.pending;C===null?p.next=p:(p.next=C.next,C.next=p),S.pending=p}}l.lanes|=n,p=l.alternate,p!==null&&(p.lanes|=n),Wl(l.return,n,t),d.lanes|=n;break}p=p.next}}else if(l.tag===10)s=l.type===t.type?null:l.child;else if(l.tag===18){if(s=l.return,s===null)throw Error(u(341));s.lanes|=n,d=s.alternate,d!==null&&(d.lanes|=n),Wl(s,n,t),s=l.sibling}else s=l.child;if(s!==null)s.return=l;else for(s=l;s!==null;){if(s===t){s=null;break}if(l=s.sibling,l!==null){l.return=s.return,s=l;break}s=s.return}l=s}it(e,t,i.children,n),t=t.child}return t;case 9:return i=t.type,r=t.pendingProps.children,Nr(t,n),i=Pt(i),r=r(i),t.flags|=1,it(e,t,r,n),t.child;case 14:return r=t.type,i=Ut(r,t.pendingProps),i=Ut(r.type,i),bu(e,t,r,i,n);case 15:return Uu(e,t,t.type,t.pendingProps,n);case 17:return r=t.type,i=t.pendingProps,i=t.elementType===r?i:Ut(r,i),Po(e,t),t.tag=1,ct(r)?(e=!0,po(t)):e=!1,Nr(t,n),Pu(t,r,i),la(t,r,i,n),ca(null,t,r,!0,e,n);case 19:return Yu(e,t,n);case 22:return $u(e,t,n)}throw Error(u(156,t.tag))};function yc(e,t){return Hi(e,t)}function Wf(e,t,n,r){this.tag=e,this.key=n,this.sibling=this.child=this.return=this.stateNode=this.type=this.elementType=null,this.index=0,this.ref=null,this.pendingProps=t,this.dependencies=this.memoizedState=this.updateQueue=this.memoizedProps=null,this.mode=r,this.subtreeFlags=this.flags=0,this.deletions=null,this.childLanes=this.lanes=0,this.alternate=null}function Ft(e,t,n,r){return new Wf(e,t,n,r)}function La(e){return e=e.prototype,!(!e||!e.isReactComponent)}function Hf(e){if(typeof e=="function")return La(e)?1:0;if(e!=null){if(e=e.$$typeof,e===H)return 11;if(e===se)return 14}return 2}function Pn(e,t){var n=e.alternate;return n===null?(n=Ft(e.tag,t,e.key,e.mode),n.elementType=e.elementType,n.type=e.type,n.stateNode=e.stateNode,n.alternate=e,e.alternate=n):(n.pendingProps=t,n.type=e.type,n.flags=0,n.subtreeFlags=0,n.deletions=null),n.flags=e.flags&14680064,n.childLanes=e.childLanes,n.lanes=e.lanes,n.child=e.child,n.memoizedProps=e.memoizedProps,n.memoizedState=e.memoizedState,n.updateQueue=e.updateQueue,t=e.dependencies,n.dependencies=t===null?null:{lanes:t.lanes,firstContext:t.firstContext},n.sibling=e.sibling,n.index=e.index,n.ref=e.ref,n}function Vo(e,t,n,r,i,l){var s=2;if(r=e,typeof e=="function")La(e)&&(s=1);else if(typeof e=="string")s=5;else e:switch(e){case _e:return tr(n.children,i,l,t);case Ue:s=8,i|=8;break;case He:return e=Ft(12,n,t,i|2),e.elementType=He,e.lanes=l,e;case B:return e=Ft(13,n,t,i),e.elementType=B,e.lanes=l,e;case ne:return e=Ft(19,n,t,i),e.elementType=ne,e.lanes=l,e;case ie:return Bo(n,i,l,t);default:if(typeof e=="object"&&e!==null)switch(e.$$typeof){case qe:s=10;break e;case nt:s=9;break e;case H:s=11;break e;case se:s=14;break e;case ye:s=16,r=null;break e}throw Error(u(130,e==null?e:typeof e,""))}return t=Ft(s,n,t,i),t.elementType=e,t.type=r,t.lanes=l,t}function tr(e,t,n,r){return e=Ft(7,e,r,t),e.lanes=n,e}function Bo(e,t,n,r){return e=Ft(22,e,r,t),e.elementType=ie,e.lanes=n,e.stateNode={isHidden:!1},e}function Pa(e,t,n){return e=Ft(6,e,null,t),e.lanes=n,e}function Ta(e,t,n){return t=Ft(4,e.children!==null?e.children:[],e.key,t),t.lanes=n,t.stateNode={containerInfo:e.containerInfo,pendingChildren:null,implementation:e.implementation},t}function Qf(e,t,n,r,i){this.tag=t,this.containerInfo=e,this.finishedWork=this.pingCache=this.current=this.pendingChildren=null,this.timeoutHandle=-1,this.callbackNode=this.pendingContext=this.context=null,this.callbackPriority=0,this.eventTimes=ol(0),this.expirationTimes=ol(-1),this.entangledLanes=this.finishedLanes=this.mutableReadLanes=this.expiredLanes=this.pingedLanes=this.suspendedLanes=this.pendingLanes=0,this.entanglements=ol(0),this.identifierPrefix=r,this.onRecoverableError=i,this.mutableSourceEagerHydrationData=null}function Ma(e,t,n,r,i,l,s,d,p){return e=new Qf(e,t,n,d,p),t===1?(t=1,l===!0&&(t|=8)):t=0,l=Ft(3,null,null,t),e.current=l,l.stateNode=e,l.memoizedState={element:r,isDehydrated:n,cache:null,transitions:null,pendingSuspenseBoundaries:null},Ql(l),e}function Kf(e,t,n){var r=3<arguments.length&&arguments[3]!==void 0?arguments[3]:null;return{$$typeof:he,key:r==null?null:""+r,children:e,containerInfo:t,implementation:n}}function xc(e){if(!e)return Sn;e=e._reactInternals;e:{if(en(e)!==e||e.tag!==1)throw Error(u(170));var t=e;do{switch(t.tag){case 3:t=t.stateNode.context;break e;case 1:if(ct(t.type)){t=t.stateNode.__reactInternalMemoizedMergedChildContext;break e}}t=t.return}while(t!==null);throw Error(u(171))}if(e.tag===1){var n=e.type;if(ct(n))return Ks(e,n,t)}return t}function wc(e,t,n,r,i,l,s,d,p){return e=Ma(n,r,!0,e,i,l,s,d,p),e.context=xc(null),n=e.current,r=ot(),i=Dn(n),l=sn(r,i),l.callback=t??null,zn(n,l,i),e.current.lanes=i,Wr(e,i,r),pt(e,r),e}function Wo(e,t,n,r){var i=t.current,l=ot(),s=Dn(i);return n=xc(n),t.context===null?t.context=n:t.pendingContext=n,t=sn(l,s),t.payload={element:e},r=r===void 0?null:r,r!==null&&(t.callback=r),e=zn(i,t,s),e!==null&&(Bt(e,i,s,l),ko(e,i,s)),s}function Ho(e){if(e=e.current,!e.child)return null;switch(e.child.tag){case 5:return e.child.stateNode;default:return e.child.stateNode}}function kc(e,t){if(e=e.memoizedState,e!==null&&e.dehydrated!==null){var n=e.retryLane;e.retryLane=n!==0&&n<t?n:t}}function Fa(e,t){kc(e,t),(e=e.alternate)&&kc(e,t)}function Yf(){return null}var Sc=typeof reportError=="function"?reportError:function(e){console.error(e)};function Ra(e){this._internalRoot=e}Qo.prototype.render=Ra.prototype.render=function(e){var t=this._internalRoot;if(t===null)throw Error(u(409));Wo(e,t,null,null)},Qo.prototype.unmount=Ra.prototype.unmount=function(){var e=this._internalRoot;if(e!==null){this._internalRoot=null;var t=e.containerInfo;Zn(function(){Wo(null,e,null,null)}),t[nn]=null}};function Qo(e){this._internalRoot=e}Qo.prototype.unstable_scheduleHydration=function(e){if(e){var t=os();e={blockedOn:null,target:e,priority:t};for(var n=0;n<vn.length&&t!==0&&t<vn[n].priority;n++);vn.splice(n,0,e),n===0&&ss(e)}};function Oa(e){return!(!e||e.nodeType!==1&&e.nodeType!==9&&e.nodeType!==11)}function Ko(e){return!(!e||e.nodeType!==1&&e.nodeType!==9&&e.nodeType!==11&&(e.nodeType!==8||e.nodeValue!==" react-mount-point-unstable "))}function _c(){}function qf(e,t,n,r,i){if(i){if(typeof r=="function"){var l=r;r=function(){var S=Ho(s);l.call(S)}}var s=wc(t,r,e,0,null,!1,!1,"",_c);return e._reactRootContainer=s,e[nn]=s.current,ii(e.nodeType===8?e.parentNode:e),Zn(),s}for(;i=e.lastChild;)e.removeChild(i);if(typeof r=="function"){var d=r;r=function(){var S=Ho(p);d.call(S)}}var p=Ma(e,0,!1,null,null,!1,!1,"",_c);return e._reactRootContainer=p,e[nn]=p.current,ii(e.nodeType===8?e.parentNode:e),Zn(function(){Wo(t,p,n,r)}),p}function Yo(e,t,n,r,i){var l=n._reactRootContainer;if(l){var s=l;if(typeof i=="function"){var d=i;i=function(){var p=Ho(s);d.call(p)}}Wo(t,s,e,i)}else s=qf(n,t,e,i,r);return Ho(s)}rs=function(e){switch(e.tag){case 3:var t=e.stateNode;if(t.current.memoizedState.isDehydrated){var n=Br(t.pendingLanes);n!==0&&(ll(t,n|1),pt(t,O()),(fe&6)===0&&(Pr=O()+500,_n()))}break;case 13:Zn(function(){var r=an(e,1);if(r!==null){var i=ot();Bt(r,e,1,i)}}),Fa(e,1)}},al=function(e){if(e.tag===13){var t=an(e,134217728);if(t!==null){var n=ot();Bt(t,e,134217728,n)}Fa(e,134217728)}},is=function(e){if(e.tag===13){var t=Dn(e),n=an(e,t);if(n!==null){var r=ot();Bt(n,e,t,r)}Fa(e,t)}},os=function(){return we},ls=function(e,t){var n=we;try{return we=e,t()}finally{we=n}},br=function(e,t,n){switch(t){case"input":if(jt(e,n),t=n.name,n.type==="radio"&&t!=null){for(n=e;n.parentNode;)n=n.parentNode;for(n=n.querySelectorAll("input[name="+JSON.stringify(""+t)+'][type="radio"]'),t=0;t<n.length;t++){var r=n[t];if(r!==e&&r.form===e.form){var i=co(r);if(!i)throw Error(u(90));On(r),jt(r,i)}}}break;case"textarea":lr(e,n);break;case"select":t=n.value,t!=null&&gt(e,!!n.multiple,t,!1)}},Ri=Ca,Oi=Zn;var Gf={usingClientEntryPoint:!1,Events:[ai,yr,co,Jt,Nt,Ca]},ki={findFiberByHostInstance:Wn,bundleType:0,version:"18.3.1",rendererPackageName:"react-dom"},Xf={bundleType:ki.bundleType,version:ki.version,rendererPackageName:ki.rendererPackageName,rendererConfig:ki.rendererConfig,overrideHookState:null,overrideHookStateDeletePath:null,overrideHookStateRenamePath:null,overrideProps:null,overridePropsDeletePath:null,overridePropsRenamePath:null,setErrorHandler:null,setSuspenseHandler:null,scheduleUpdate:null,currentDispatcherRef:pe.ReactCurrentDispatcher,findHostInstanceByFiber:function(e){return e=Bi(e),e===null?null:e.stateNode},findFiberByHostInstance:ki.findFiberByHostInstance||Yf,findHostInstancesForRefresh:null,scheduleRefresh:null,scheduleRoot:null,setRefreshHandler:null,getCurrentFiber:null,reconcilerVersion:"18.3.1-next-f1338f8080-20240426"};if(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__<"u"){var qo=__REACT_DEVTOOLS_GLOBAL_HOOK__;if(!qo.isDisabled&&qo.supportsFiber)try{Bn=qo.inject(Xf),R=qo}catch{}}return ht.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED=Gf,ht.createPortal=function(e,t){var n=2<arguments.length&&arguments[2]!==void 0?arguments[2]:null;if(!Oa(t))throw Error(u(200));return Kf(e,t,null,n)},ht.createRoot=function(e,t){if(!Oa(e))throw Error(u(299));var n=!1,r="",i=Sc;return t!=null&&(t.unstable_strictMode===!0&&(n=!0),t.identifierPrefix!==void 0&&(r=t.identifierPrefix),t.onRecoverableError!==void 0&&(i=t.onRecoverableError)),t=Ma(e,1,!1,null,null,n,!1,r,i),e[nn]=t.current,ii(e.nodeType===8?e.parentNode:e),new Ra(t)},ht.findDOMNode=function(e){if(e==null)return null;if(e.nodeType===1)return e;var t=e._reactInternals;if(t===void 0)throw typeof e.render=="function"?Error(u(188)):(e=Object.keys(e).join(","),Error(u(268,e)));return e=Bi(t),e=e===null?null:e.stateNode,e},ht.flushSync=function(e){return Zn(e)},ht.hydrate=function(e,t,n){if(!Ko(t))throw Error(u(200));return Yo(null,e,t,!0,n)},ht.hydrateRoot=function(e,t,n){if(!Oa(e))throw Error(u(405));var r=n!=null&&n.hydratedSources||null,i=!1,l="",s=Sc;if(n!=null&&(n.unstable_strictMode===!0&&(i=!0),n.identifierPrefix!==void 0&&(l=n.identifierPrefix),n.onRecoverableError!==void 0&&(s=n.onRecoverableError)),t=wc(t,null,e,1,n??null,i,!1,l,s),e[nn]=t.current,ii(e),r)for(e=0;e<r.length;e++)n=r[e],i=n._getVersion,i=i(n._source),t.mutableSourceEagerHydrationData==null?t.mutableSourceEagerHydrationData=[n,i]:t.mutableSourceEagerHydrationData.push(n,i);return new Qo(t)},ht.render=function(e,t,n){if(!Ko(t))throw Error(u(200));return Yo(null,e,t,!1,n)},ht.unmountComponentAtNode=function(e){if(!Ko(e))throw Error(u(40));return e._reactRootContainer?(Zn(function(){Yo(null,null,e,!1,function(){e._reactRootContainer=null,e[nn]=null})}),!0):!1},ht.unstable_batchedUpdates=Ca,ht.unstable_renderSubtreeIntoContainer=function(e,t,n,r){if(!Ko(n))throw Error(u(200));if(e==null||e._reactInternals===void 0)throw Error(u(38));return Yo(e,t,n,!1,r)},ht.version="18.3.1-next-f1338f8080-20240426",ht}var Pc;function lp(){if(Pc)return ba.exports;Pc=1;function o(){if(!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__>"u"||typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE!="function"))try{__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(o)}catch(c){console.error(c)}}return o(),ba.exports=op(),ba.exports}var Tc;function ap(){if(Tc)return Go;Tc=1;var o=lp();return Go.createRoot=o.createRoot,Go.hydrateRoot=o.hydrateRoot,Go}var sp=ap();const up=Yc(sp),cp="modulepreload",dp=function(o,c){return new URL(o,c).href},Mc={},fp=function(c,u,f){let g=Promise.resolve();if(u&&u.length>0){let k=function(G){return Promise.all(G.map(q=>Promise.resolve(q).then(te=>({status:"fulfilled",value:te}),te=>({status:"rejected",reason:te}))))};const N=document.getElementsByTagName("link"),F=document.querySelector("meta[property=csp-nonce]"),X=(F==null?void 0:F.nonce)||(F==null?void 0:F.getAttribute("nonce"));g=k(u.map(G=>{if(G=dp(G,f),G in Mc)return;Mc[G]=!0;const q=G.endsWith(".css"),te=q?'[rel="stylesheet"]':"";if(!!f)for(let M=N.length-1;M>=0;M--){const K=N[M];if(K.href===G&&(!q||K.rel==="stylesheet"))return}else if(document.querySelector(`link[href="${G}"]${te}`))return;const E=document.createElement("link");if(E.rel=q?"stylesheet":cp,q||(E.as="script"),E.crossOrigin="",E.href=G,X&&E.setAttribute("nonce",X),document.head.appendChild(E),q)return new Promise((M,K)=>{E.addEventListener("load",M),E.addEventListener("error",()=>K(new Error(`Unable to preload CSS for ${G}`)))})}))}function x(k){const N=new Event("vite:preloadError",{cancelable:!0});if(N.payload=k,window.dispatchEvent(N),!N.defaultPrevented)throw k}return g.then(k=>{for(const N of k||[])N.status==="rejected"&&x(N.reason);return c().catch(x)})},pp=[" in provincia","mercato settimanale a ","fiere, mostre e mercati"," http://"," https://"," il mercato settimanale di "],hp=new Set(["AL","BS","MI","BG","BO","FI","RM","NA"]);function qc(o){const c=String(o||"").trim(),u=c.toLocaleLowerCase("it");return c.length>68||c.startsWith('"')||c.startsWith("“")||c.startsWith("”")||hp.has(c.toUpperCase())||pp.some(f=>u.includes(f))||/^(via|viale|corso)\s/i.test(c)&&c.includes("-")}function gp(o){return qc(o)?"Località da verificare":String(o||"")}const mp="La località riportata dalla fonte non identifica con sicurezza un Comune. Controlla la fonte originale prima di spostarti.",Gc=new Set(["arezzonotizie.it","baritoday.it","bolognatoday.it","bresciatoday.it","cagliaritoday.it","casertanews.it","cataniatoday.it","cesenatoday.it","ferraratoday.it","firenzetoday.it","forlitoday.it","frosinonetoday.it","genovatoday.it","leccotoday.it","modenatoday.it","monzatoday.it","novaratoday.it","padovatoday.it","palermotoday.it","parmatoday.it","ravennatoday.it","riminitoday.it","romatoday.it","torinotoday.it","trevisotoday.it","veneziatoday.it","vicenzatoday.it","viterbotoday.it"]),vp=[1116352408,1899447441,3049323471,3921009573,961987163,1508970993,2453635748,2870763221,3624381080,310598401,607225278,1426881987,1925078388,2162078206,2614888103,3248222580,3835390401,4022224774,264347078,604807628,770255983,1249150122,1555081692,1996064986,2554220882,2821834349,2952996808,3210313671,3336571891,3584528711,113926993,338241895,666307205,773529912,1294757372,1396182291,1695183700,1986661051,2177026350,2456956037,2730485921,2820302411,3259730800,3345764771,3516065817,3600352804,4094571909,275423344,430227734,506948616,659060556,883997877,958139571,1322822218,1537002063,1747873779,1955562222,2024104815,2227730452,2361852424,2428436474,2756734187,3204031479,3329325298],qt=(o,c)=>o>>>c|o<<32-c;function yp(o){const c=new Uint8Array(Math.ceil((o.length+9)/64)*64);for(let x=0;x<o.length;x++)c[x]=o.charCodeAt(x);c[o.length]=128;const u=new DataView(c.buffer);u.setUint32(c.length-4,o.length*8);const f=[1779033703,3144134277,1013904242,2773480762,1359893119,2600822924,528734635,1541459225],g=new Uint32Array(64);for(let x=0;x<c.length;x+=64){for(let M=0;M<16;M++)g[M]=u.getUint32(x+M*4);for(let M=16;M<64;M++){const K=g[M-15],Z=g[M-2];g[M]=g[M-16]+(qt(K,7)^qt(K,18)^K>>>3)+g[M-7]+(qt(Z,17)^qt(Z,19)^Z>>>10)}let[k,N,F,X,G,q,te,_]=f;for(let M=0;M<64;M++){const K=_+(qt(G,6)^qt(G,11)^qt(G,25))+(G&q^~G&te)+vp[M]+g[M]>>>0,Z=(qt(k,2)^qt(k,13)^qt(k,22))+(k&N^k&F^N&F)>>>0;_=te,te=q,q=G,G=X+K>>>0,X=F,F=N,N=k,k=K+Z>>>0}const E=[k,N,F,X,G,q,te,_];for(let M=0;M<f.length;M++)f[M]=f[M]+E[M]>>>0}return f.map(x=>x.toString(16).padStart(8,"0")).join("")}function Xc(o){if(typeof o!="string"||o.length<20||o.length>1200)return null;const c=o.match(/^https:\/\/www\.([a-z]+\.it)\/eventi\/(?!tipo\/|location\/)[A-Za-z0-9][A-Za-z0-9_/-]*\.html$/);return!c||c[0]!==o||!Gc.has(c[1])?null:[c[1],"citynews-"+yp(o).slice(0,24)]}const Fc={indirizzo:"Sede",orario_testo:"Orari",ricorrenza_testo:"Giorni"},Rc=o=>typeof o=="string"&&/^\d{4}-\d{2}-\d{2}$/.test(o)&&Number.isFinite(Date.parse(`${o}T00:00:00Z`))&&new Date(`${o}T00:00:00Z`).toISOString().slice(0,10)===o;function xp(o,c=new Date().toISOString().slice(0,10)){if(!Array.isArray(o.riscontri_campi))return[];const u={slug:o.slug||o.id,citta:o.citta||"",provincia:o.provincia||"",regione:o.regione||""};return o.riscontri_campi.slice(0,6).flatMap(f=>{if(!f||f.schema!==1||!f.mercato||!f.valori||Object.entries(u).some(([N,F])=>f.mercato[N]!==F)||!Rc(f.letto_il)||f.letto_il>c||f.fonte_aggiornata_il&&(!Rc(f.fonte_aggiornata_il)||f.fonte_aggiornata_il>f.letto_il))return[];let g;try{g=new URL(f.url)}catch{return[]}if(g.protocol!=="https:"||g.username||g.password)return[];const x=Xc(f.url);if((x||Gc.has(f.fonte)||f.gestore_campi==="citynews_detail"||String(f.fonte_id||"").startsWith("citynews-"))&&(!x||f.url!==o.url_fonte||f.fonte!==x[0]||f.fonte_id!==x[1]||f.riga_fonte!==x[1]+":event-card"||f.metodo!=="pagina_primaria_revisionata"||f.ambito!=="pagina"||f.impronta_tipo!=="html_bytes"||!/^[a-f0-9]{64}$/.test(f.sha256||"")||f.fonte_aggiornata_il))return[];const k=Object.keys(Fc).filter(N=>typeof f.valori[N]=="string"&&f.valori[N]&&f.valori[N]===o[N]);return k.length?[{fields:k.map(N=>Fc[N]).join(", "),readOn:f.letto_il,sourceDate:f.fonte_aggiornata_il||"",sourceName:String(f.fonte||"Fonte"),sourceUrl:g.href}]:[]})}const wp=["schema","gestore","campo","mercato","valore_catalogo","valore_fonte","giorno_settimana","url_richiesto","url_finale","letto_il","sha256","bytes","prova"],Oc=["slug","nome","citta","provincia","regione","fonte","url_fonte"],kp={slug:130,nome:160,citta:120,provincia:2,regione:80,fonte:100,url_fonte:650},Sp=["tipo","selettore","frammento","sede_precedente","sede_attuale"],_p="queste indicazioni sostituiscono i vecchi riferimenti",Ic=/^main#main article\.hpe-editorial--local-guide \.hpe-editorial-grid > \.hpe-editorial-body > p:nth-child\(([1-9]\d{0,2})\)$/,jp=new Set(["centro","centro storico","sede da verificare","da verificare","piazza","via","viale","citta","zona centro","non disponibile","sconosciuto","varie sedi"]),zp=["mercati in ","mercati settimanali","sagra","fiera","su richiesta","consultare","da definire","presso gli stand"],Np=new RegExp("^(?:via|viale|vicolo|vico|corso|piazza|piazzale|piazzetta|largo|lungomare|strada|villaggio|campo|parco|borgo|frazione|contrada|passeggiata(?=\\s+(?:d|di|del|della|dell|dei|delle|degli)(?:\\s+|['’])\\p{L}))(?![\\p{L}\\p{N}_])","iu"),el=o=>o!==null&&typeof o=="object"&&!Array.isArray(o),Va=(o,c)=>el(o)&&Object.keys(o).length===c.length&&c.every(u=>Object.hasOwn(o,u)),nr=(o,c)=>typeof o=="string"&&o.length>0&&[...o].length<=c&&o===o.split(/[\s\u0085]+/u).filter(Boolean).join(" ")&&!/[\u0000-\u001f\u007f]/.test(o),Cp=o=>o.normalize("NFKD").replace(new RegExp("\\p{Mark}","gu"),"").toLowerCase().replace(/ß/g,"ss").replace(/\s+/g," ").trim(),Mr=o=>(o.normalize("NFKD").replace(new RegExp("\\p{Mark}","gu"),"").toLowerCase().match(/[a-z0-9]+/g)||[]).join(" "),Ac=o=>typeof o=="string"&&/^\d{4}-\d{2}-\d{2}$/.test(o)&&Number.isFinite(Date.parse(o+"T00:00:00Z"))&&new Date(o+"T00:00:00Z").toISOString().slice(0,10)===o,Ga=()=>new Date().toISOString().slice(0,10);function Zc(o){if(typeof o!="string"||!/^https:\/\/[^/]/i.test(o)||o.includes("\\")||o!==o.trim())return null;try{const c=new URL(o);return c.protocol==="https:"&&c.hostname&&!c.username&&!c.password&&!c.port&&!c.hash?c:null}catch{return null}}function bc(o){var f;const c=Zc(o);if(!c||c.hostname!=="www.happings.com"||c.port||c.search)return null;const u=o.match(/^https:\/\/([^/?#]+)(\/[^?#]*)/i);return!u||!/^www\.happings\.com(?::443)?$/i.test(u[1])?null:((f=u[2].match(/^\/it\/mercati-settimanali-(?:a|ad)-([a-z0-9]+(?:-[a-z0-9]+)*?)(?:\.html|-e-provincia\/)$/))==null?void 0:f[1])||null}function Uc(o){if(typeof o!="string"||[...o].length<7||[...o].length>190)return!1;const c=Cp(o);return Np.test(c)&&!jp.has(Mr(o))&&!zp.some(u=>c.includes(u))}function Ep(o,c,u=Ga()){if(!el(c)||!Va(o,wp)||o.schema!==1||o.gestore!=="happings-weekly"||o.campo!=="indirizzo"||!Va(o.mercato,Oc)||Oc.some(N=>!nr(o.mercato[N],kp[N])||o.mercato[N]!==(N==="slug"?c.slug||c.id:c[N]))||!/^[A-Z]{2}$/.test(o.mercato.provincia)||!Zc(o.mercato.url_fonte)||o.valore_catalogo!==c.indirizzo||!nr(o.valore_catalogo,190)||!nr(o.valore_fonte,190)||!Uc(o.valore_catalogo)||!Uc(o.valore_fonte)||Mr(o.valore_catalogo)===Mr(o.valore_fonte)||!Number.isInteger(o.giorno_settimana)||o.giorno_settimana<0||o.giorno_settimana>6||!Ac(u)||!Ac(o.letto_il)||o.letto_il>u||typeof o.sha256!="string"||!/^[a-f0-9]{64}$/.test(o.sha256)||!Number.isInteger(o.bytes)||o.bytes<1||o.bytes>26e5||!nr(o.url_richiesto,650)||!nr(o.url_finale,650))return!1;const f=bc(o.url_richiesto);if(!f||f!==bc(o.url_finale))return!1;const g=o.prova;if(!Va(g,Sp)||g.tipo!=="sostituzione_sede_esplicita"||!nr(g.selettore,200)||!Ic.test(g.selettore)||Number(g.selettore.match(Ic)[1])>200||!nr(g.frammento,1200)||g.sede_precedente!==o.valore_catalogo||g.sede_attuale!==o.valore_fonte)return!1;const k=Mr(g.frammento).split(_p);return k.length===2&&(" "+k[0]+" ").includes(" "+Mr(g.sede_attuale)+" ")&&(" "+k[1]+" ").includes(" "+Mr(g.sede_precedente)+" ")}function Xa(o,c,u=Ga()){if(!Array.isArray(o)||o.length>3)return[];const f=x=>Array.isArray(x)?x.map(f):el(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,f(x[k])])):x;return[...new Map(o.filter(x=>Ep(x,c,u)).map(x=>{const k=f(x);return[JSON.stringify(k),k]})).values()].sort((x,k)=>{const N=[x.letto_il,x.url_finale,x.sha256,x.valore_fonte,x.prova.selettore,x.prova.frammento],F=[k.letto_il,k.url_finale,k.sha256,k.valore_fonte,k.prova.selettore,k.prova.frammento];for(let X=0;X<N.length;X++)if(N[X]!==F[X])return N[X]>F[X]?-1:1;return 0})}function Fr(o,c=Ga()){if(!el(o))return[];const u={slug:o.id,nome:o.name,citta:o.originalCity,provincia:o.province,regione:o.region,fonte:o.source,url_fonte:o.sourceUrl,indirizzo:o.address};return Xa(o.fieldConflicts,u,c).map(f=>({key:[f.sha256,f.valore_fonte,f.giorno_settimana].join("/"),savedAddress:f.valore_catalogo,sourceAddress:f.valore_fonte,sourceUrl:f.url_finale,readOn:f.letto_il,readOnLabel:new Date(f.letto_il+"T12:00:00Z").toLocaleDateString("it-IT",{day:"numeric",month:"short",year:"numeric",timeZone:"UTC"})}))}const Dp="./",Jc=1800*1e3;let Ni=0,_i=null;const ed="mercati_preferiti";let Ci;const Ei=new Map,$c=["slug","nome","citta","regione","categoria","tags","lat","lng","position_quality","orario_testo","date_quality","date"],td=new Set(["","per_data","storico"]);function Lp(o,c){const u=c.index_schema,f=[4,5,6].includes(u),g=u===void 0||[1,2,3].includes(u);if(!f&&!g)throw new Error("Versione indice non supportata");if(u===6){const k=c.index_as_of,N=typeof k=="string"&&/^\d{4}-\d{2}-\d{2}$/.test(k)?new Date(k+"T12:00:00Z"):null;if(!N||!Number.isFinite(N.getTime())||N.toISOString().slice(0,10)!==k)throw new Error("Data di riferimento indice non valida")}const x=u===6?[...$c,"ambito_orari"]:$c;return o.map(k=>{if(!Array.isArray(k)){if(!g||!k||typeof k!="object")throw new Error("Formato indice errato");return{...k,ambito_orari:""}}if(u!==void 0&&!f||k.length!==x.length||u===6&&!td.has(k[x.length-1]))throw new Error("Formato indice errato");return Object.fromEntries(x.map((N,F)=>[N,k[F]]))})}function Pp(o){if(typeof o!="string"||!/^data\/v1\/[a-zA-Z0-9._/-]+\.json$/.test(o)||o.includes(".."))throw new Error("Percorso catalogo non valido");return Dp.replace(/\/$/,"/")+o}async function Li(o,c=!1,u=!1,f=Date.now()){let g=Pp(o);if(o==="data/v1/manifest.json"){if(!Number.isFinite(f)||f<0)throw new Error("Data controllo catalogo non valida");g+="?refresh="+Math.floor(f/Jc)}const x=await fetch(g,{cache:c?"force-cache":u?"no-cache":"default"});if(!x.ok)throw new Error("Catalogo non disponibile: "+o+" ("+x.status+")");return x.json()}async function Tp(o,c,u){let f=0;const g=new Array(o.length);return await Promise.all(Array.from({length:Math.min(o.length,c)},async()=>{for(;f<o.length;){const x=f++;g[x]=await u(o[x],x)}})),g}async function nd(o){if(o.schema!==1||!Number.isInteger(o.total)||o.total<0)throw new Error("Manifest del catalogo non valido");if(o.index){const x=await Li(o.index,!0);if(x.schema!==1||!Array.isArray(x.markets)||x.markets.length!==o.total)throw new Error("Indice mercati incompleto");const k=Lp(x.markets,o),N=new Set;for(const F of k){if(!F.slug||N.has(F.slug))throw new Error("Indice duplicato o non valido");N.add(F.slug)}return{manifest:o,markets:k}}let c;if(o.layout==="single")c=[{path:o.catalog}];else if(o.layout==="regional"&&Array.isArray(o.regions))c=o.regions;else throw new Error("Formato catalogo non supportato");const f=(await Tp(c,4,async x=>{const k=await Li(x.path,!0);if(k.schema!==1||!Array.isArray(k.markets))throw new Error("File mercati non valido: "+x.path);if(x.count!==void 0&&k.markets.length!==x.count)throw new Error("Conteggio non valido: "+x.path);return k.markets})).flat();if(f.length!==o.total)throw new Error("Catalogo incompleto");const g=new Set;for(const x of f){if(!x.slug||g.has(x.slug))throw new Error("ID mercato duplicato o assente");g.add(x.slug)}return{manifest:o,markets:f}}async function Mp(){const o=Date.now(),c=await nd(await Li("data/v1/manifest.json",!1,!1,o));return Ni=o,c}function Fp(o,c=Date.now()){return Number.isFinite(c)&&(!o||c>=o&&c-o>=Jc)}async function Rp(o=Date.now()){const c=await Za();if(_i)return _i;if(!Fp(Ni,o))return!1;Ni=o,_i=(async()=>{const u=await Li("data/v1/manifest.json",!1,!0,o);if(u.content_signature&&c.manifest.content_signature&&u.content_signature===c.manifest.content_signature&&u.index===c.manifest.index)return Ni=o,!1;const f=await nd(u);return Ci=Promise.resolve(f),Ei.clear(),Ni=o,!0})();try{return await _i}finally{_i=null}}async function Za(){return Ci||(Ci=Mp().catch(o=>{throw Ci=null,o})),Ci}function Op(o=new Date){return[o.getFullYear(),String(o.getMonth()+1).padStart(2,"0"),String(o.getDate()).padStart(2,"0")].join("-")}function Ip(o=[]){const c=Op();return(o||[]).filter(u=>typeof u=="string"&&u>=c).sort()[0]||null}function Ap(o,c,u,f){if(![o,c,u,f].every(Number.isFinite))return 1/0;const g=Math.PI/180,x=(u-o)*g,k=(f-c)*g,N=Math.sin(x/2)**2+Math.cos(o*g)*Math.cos(u*g)*Math.sin(k/2)**2;return 6371*2*Math.atan2(Math.sqrt(N),Math.sqrt(1-N))}function Ha(o,c,u){const f=typeof o.lat=="number"&&Number.isFinite(o.lat)?o.lat:null,g=typeof o.lng=="number"&&Number.isFinite(o.lng)?o.lng:null;return{id:o.slug,nome:o.nome||"",citta:o.citta||"",provincia:o.provincia||"",regione:o.regione||"",indirizzo:o.indirizzo||"",lat:f,lng:g,categoria:o.categoria||"misto",tags:o.tags||[],orario_testo:o.orario_testo||"",ambito_orari:td.has(o.ambito_orari)?o.ambito_orari:"",ricorrenza_testo:o.ricorrenza_testo||"",descrizione:o.descrizione||"",date:o.date||[],prossima_data:Ip(o.date),confidence:o.confidence??0,completezza:o.completezza??0,verificato_il:o.verificato_il||"",aggiornato_il:o.aggiornato_il||"",aggiornamento_ambito:o.aggiornamento_ambito||"",importato_il:o.importato_il||"",fonte_letta_il:o.fonte_letta_il||"",fonte_aggiornata_il:o.fonte_aggiornata_il||"",riscontri_campi:Array.isArray(o.riscontri_campi)?o.riscontri_campi:[],conflitti_campi:Xa(o.conflitti_campi,o),eccezioni_calendario:Array.isArray(o.eccezioni_calendario)?o.eccezioni_calendario:[],calendario_fonte:o.calendario_fonte&&typeof o.calendario_fonte=="object"&&!Array.isArray(o.calendario_fonte)?o.calendario_fonte:null,dettaglio_fonte:o.dettaglio_fonte&&typeof o.dettaglio_fonte=="object"&&!Array.isArray(o.dettaglio_fonte)?o.dettaglio_fonte:null,evidenza_editoriale:o.evidenza_editoriale&&typeof o.evidenza_editoriale=="object"&&!Array.isArray(o.evidenza_editoriale)?o.evidenza_editoriale:null,date_quality:o.date_quality||"prevista",position_quality:o.position_quality||"sconosciuta",status:o.status||"non_confermato",fonte:o.fonte||"",url_fonte:o.url_fonte||"",navigazione_sospesa_motivo:o.navigazione_sospesa_motivo||"",coordinate_sospese_motivo:o.coordinate_sospese_motivo||"",fonti:Array.isArray(o.fonti)?o.fonti.filter(x=>x&&typeof x.nome=="string"&&typeof x.url=="string"):[],distance:Number.isFinite(c)&&Number.isFinite(u)&&Number.isFinite(f)&&Number.isFinite(g)?Ap(c,u,f,g):null}}async function bp({userLat:o=null,userLng:c=null}={}){const{markets:u}=await Za();return u.map(f=>Ha(f,o,c))}async function Up(o){const{manifest:c,markets:u}=await Za(),f=u.find(N=>N.slug===o);if(!f)return null;if(!c.index)return Ha(f,null,null);const g=c.layout==="single"?{path:c.catalog}:c.regions.find(N=>N.name===f.regione);if(!g)throw new Error("Dettagli non disponibili per la regione");if(!Ei.has(g.path)){const N=Li(g.path,!0).then(F=>{if(F.schema!==1||!Array.isArray(F.markets))throw new Error("Dati regionali non validi");if(g.count!==void 0&&F.markets.length!==g.count)throw new Error("Catalogo regionale incompleto");return F.markets}).catch(F=>{throw Ei.delete(g.path),F});Ei.set(g.path,N)}const k=(await Ei.get(g.path)).find(N=>N.slug===o);if(!k)throw new Error("Mercato non trovato nel file regionale");return Ha(k,null,null)}function $p(){return"static"}function rd(){try{return new Set(JSON.parse(localStorage.getItem(ed)||"[]"))}catch{return new Set}}async function Vp(){return rd()}async function Bp(o){const c=rd();c.has(o)?c.delete(o):c.add(o);try{localStorage.setItem(ed,JSON.stringify([...c]))}catch{}return c}const Wp={alimentare:"Alimentare",antiquariato:"Antiquariato",vintage_abbigliamento:"Vintage e abbigliamento",usato:"Usato",artigianato:"Artigianato",misto:"Misto"},Hp={Alimentare:"🍅",Antiquariato:"🏺","Vintage e abbigliamento":"👗",Usato:"📦",Artigianato:"🎨",Misto:"🎪"},Qp={Alimentare:"#446E47",Antiquariato:"#B94439","Vintage e abbigliamento":"#705073",Usato:"#805B08",Artigianato:"#216886",Misto:"#9C4B36"};function Vc(o,c,u){const f=Wp[o.categoria]||o.categoria||"Misto",g=qc(o.citta)||o.navigazione_sospesa_motivo==="indirizzo_e_punto_sorgente_non_riconciliati",x={id:o.id,name:o.nome,city:gp(o.citta),originalCity:o.citta,province:o.provincia||"",locationReviewRequired:g,region:o.regione,address:o.indirizzo||"",lat:o.lat,lng:o.lng,category:f,tags:o.tags||[],dates:o.date||[],hours:o.orario_testo||"",indexHoursScope:o.ambito_orari||"",recurrence:o.ricorrenza_testo||"",description:o.descrizione||"",source:o.fonte||"",confidence:o.confidence??0,dataCompleteness:o.completezza??0,sourceUpdated:o.fonte_aggiornata_il?o.fonte_aggiornata_il.slice(0,10):"",sourceUpdateScope:o.aggiornamento_ambito||"",lastVerified:o.verificato_il?o.verificato_il.slice(0,10):"",dateQuality:o.date_quality||"prevista",positionQuality:o.position_quality||"sconosciuta",status:o.status||"non_confermato",sourceUrl:o.url_fonte||"",sourceEvidence:Array.isArray(o.fonti)?o.fonti.filter(k=>k&&k.url&&k.nome):[],fieldEvidence:xp(o),fieldConflicts:Xa(o.conflitti_campi,o),calendarExceptions:Array.isArray(o.eccezioni_calendario)?o.eccezioni_calendario:[],sourceCalendar:o.calendario_fonte||null,sourceDetail:o.dettaglio_fonte||null,editorialEvidence:o.evidenza_editoriale||null,distance:Number.isFinite(o.distance)?o.distance:null};return{...x,addressReviewRequired:Fr(x).length>0}}function Kp(){const[o,c]=U.useState([]),[u,f]=U.useState(!0),[g,x]=U.useState(0),k=null,[N,F]=U.useState(null),[X,G]=U.useState(new Set),[q,te]=U.useState({regioni:[],citta:[]}),[_,E]=U.useState(null),[M,K]=U.useState("idle"),[Z,ae]=U.useState(""),ze=(_==null?void 0:_.lat)??null,pe=(_==null?void 0:_.lng)??null,Me=$p(),he=U.useCallback(()=>{if(typeof navigator>"u"||!navigator.geolocation){K("unavailable"),ae("La posizione non è disponibile su questo dispositivo.");return}K("requesting"),ae(""),navigator.geolocation.getCurrentPosition(B=>{var ye,ie;const ne=(ye=B==null?void 0:B.coords)==null?void 0:ye.latitude,se=(ie=B==null?void 0:B.coords)==null?void 0:ie.longitude;if(!Number.isFinite(ne)||!Number.isFinite(se)){K("error"),ae("Non sono riuscito a leggere la posizione.");return}E({lat:ne,lng:se}),K("ready"),ae("")},B=>{K((B==null?void 0:B.code)===1?"denied":"error"),ae((B==null?void 0:B.code)===1?"Accesso alla posizione negato. Puoi cercare per città.":"Posizione non disponibile. Puoi cercare per città.")},{enableHighAccuracy:!1,timeout:12e3,maximumAge:3e5})},[]),_e=U.useCallback(()=>{E(null),K("idle"),ae("")},[]);U.useEffect(()=>{let B=!0;const ne=()=>{document.visibilityState!=="hidden"&&Rp().then(ye=>{B&&ye&&x(ie=>ie+1)}).catch(()=>{})};document.addEventListener("visibilitychange",ne),window.addEventListener("focus",ne);const se=window.setInterval(ne,1800*1e3);return()=>{B=!1,document.removeEventListener("visibilitychange",ne),window.removeEventListener("focus",ne),window.clearInterval(se)}},[]),U.useEffect(()=>{let B=!1;async function ne(){try{f(!0);const[se,ye]=await Promise.all([bp({userLat:ze,userLng:pe}),Vp()]),ie=se.map(A=>Vc(A,ze,pe)),T={regioni:[...new Set(ie.map(A=>A.region).filter(Boolean))].sort(),citta:[...new Set(ie.filter(A=>!A.locationReviewRequired).map(A=>A.city).filter(Boolean))].sort()};if(B)return;c(ie),G(ye),te(T),F(null)}catch(se){B||F(se.message)}finally{B||f(!1)}}return ne(),()=>{B=!0}},[ze,pe,g]);const Ue=U.useCallback(async B=>{G(ne=>{const se=new Set(ne);return se.has(B)?se.delete(B):se.add(B),se});try{const ne=await Bp(B);G(ne)}catch{}},[]),He=U.useCallback(async B=>{const ne=await Up(B);return ne?Vc(ne):null},[ze,pe]),qe=U.useMemo(()=>["Alimentare","Antiquariato","Vintage e abbigliamento","Usato","Artigianato","Misto"],[]),nt=U.useMemo(()=>q.regioni.length>0?q.regioni:[...new Set(o.map(B=>B.region))].sort(),[q.regioni,o]),H=U.useMemo(()=>q.citta.length>0?q.citta:[...new Set(o.map(B=>B.city))].sort(),[q.citta,o]);return{markets:o,loading:u,error:N,seedStatus:k,favorites:X,toggleFav:Ue,getMarketDetails:He,categories:qe,regions:nt,cities:H,categoryIcons:Hp,categoryColors:Qp,dataMode:Me,userLat:ze,userLng:pe,positionStatus:M,positionError:Z,requestPosition:he,clearPosition:_e}}const id=["Lun","Mar","Mer","Gio","Ven","Sab","Dom"];function Ye(o){return String(o||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("it").replace(/[’']/g," ").replace(/[^a-z0-9]+/g," ").trim().replace(/\s+/g," ")}function od(o){const c=Ye(o==null?void 0:o.name),u=Ye(o==null?void 0:o.city);if(!c||!u||!(o!=null&&o.region))return!1;const f=c.match(/^mercat(?:o|ino) settimanale (?:di|a|ad|del|della|dei|in|nel|nella) (.+)$/);return!!(f&&f[1]===u)}function Yp(o){return`weekly:${Ye(o.region)}:${Ye(o.city)}`}function Pi(o){if(typeof o!="string"||!/^\d{4}-\d\d-\d\d$/.test(o))return null;const c=new Date(o+"T12:00:00");return Number.isNaN(c.getTime())||c.getFullYear()!==Number(o.slice(0,4))||c.getMonth()+1!==Number(o.slice(5,7))||c.getDate()!==Number(o.slice(8))?null:(c.getDay()+6)%7}function Zo(o=[],c=null,u=new Date){const f=[u.getFullYear(),String(u.getMonth()+1).padStart(2,"0"),String(u.getDate()).padStart(2,"0")].join("-");return o.filter(g=>g>=f&&(c===null||Pi(g)===c)).sort()[0]||null}function qp(o,{keepSingleWeeklyGroups:c=!1}={}){const u=[],f=new Map;for(const g of o){if(!od(g)){u.push({kind:"market",key:g.id,market:g});continue}const x=Yp(g);let k=f.get(x);k||(k={kind:"group",key:x,city:g.city,region:g.region,markets:[]},f.set(x,k),u.push(k)),k.markets.push(g)}return u.flatMap(g=>g.kind==="group"&&g.markets.length===1&&!c?[{kind:"market",key:g.markets[0].id,market:g.markets[0]}]:[g])}function Gp(o,c,u="",f=""){if(c===null)return!1;const g=Ye(o.city);return!!u&&g===Ye(u)||!!f.trim()&&g===Ye(f.trim())}function Xp(o,c){if(!o||!c||o.id===c.id||![o,c].every(od)||[o,c].some(K=>/^(lo-mercap-|bo-open-|pg-corciano-)/.test(K.id||""))||Ye(o.region)!==Ye(c.region)||Ye(o.city)!==Ye(c.city)||Ye(o.category)!==Ye(c.category))return!1;const u=Qa(o.address),f=Qa(c.address);if(!u||u!==f||!o.sourceUrl||o.sourceUrl!==c.sourceUrl||!/^https:\/\//i.test(o.sourceUrl)||o.dateQuality!=="prevista"||c.dateQuality!=="prevista"||o.lastVerified||c.lastVerified||(o.status||"non_confermato")!==(c.status||"non_confermato"))return!1;const g=Ye(o.hours),x=Ye(c.hours);if(g&&x&&g!==x)return!1;const k=[...new Set(o.dates||[])].sort(),N=[...new Set(c.dates||[])].sort();if(k.length<2||N.length<2||k[0]!==N[0]||k[1]!==N[1])return!1;const F=Pi(k[0]);if(F===null||F!==Pi(k[1]))return!1;const[X,G,q]=k[0].split("-").map(Number),[te,_,E]=k[1].split("-").map(Number);if(Date.UTC(te,_-1,E)-Date.UTC(X,G-1,q)!==6048e5||![o,c].every(K=>{const Z=Ye(K.recurrence);return Z.includes("settimanale")&&!/mensil|quindicinal|alternat/.test(Z)}))return!1;if([o.lat,o.lng,c.lat,c.lng].every(Number.isFinite)){const Z=111.2*Math.cos((o.lat+c.lat)/2*Math.PI/180);if(Math.hypot((o.lat-c.lat)*111.2,(o.lng-c.lng)*Z)>.25)return!1}return!0}function Zp(o){return[...o].sort((c,u)=>{const f=g=>{var x;return+!!g.hours*8+ +!!g.description*3+ +!!((x=g.sourceEvidence)!=null&&x.length)*2+(Number(g.dataCompleteness)||0)/100};return f(u)-f(c)||String(u.sourceUpdated||"").localeCompare(String(c.sourceUpdated||""))||String(c.id).localeCompare(String(u.id))})[0]}function Jp(o=[]){const c=[];for(const u of o){const f=c.find(g=>g.records.every(x=>Xp(x,u)));f?f.records.push(u):c.push({records:[u]})}return c.map(u=>{const f=Zp(u.records);return{key:f.id,market:f,records:[...u.records].sort((g,x)=>String(g.id).localeCompare(String(x.id)))}})}function eh(o){const c=new Set;for(const u of o)for(const f of u.dates||[]){const g=Pi(f);g!==null&&c.add(g)}return[...c].sort((u,f)=>u-f)}function Qa(o){const c=String(o||"").trim(),u=Ye(c);return!u||u.length<7||["centro","centro storico","da definire","non disponibile","sconosciuto","non verificato","sede da verificare","citta","varie sedi"].includes(u)?"":u}function th(o,c){return o.positionQuality!=="precisa"||c.positionQuality!=="precisa"||![o.lat,o.lng,c.lat,c.lng].every(Number.isFinite)?!1:Math.abs(o.lat-c.lat)>.0025||Math.abs(o.lng-c.lng)>.0025}function nh(o){const c=[],u=new Map;for(const f of o){const g=Qa(f.address);let x=null;if(g){for(const k of u.get(g)||[])if(!th(k.markets[0],f)){x=k;break}}x||(x={key:g?`venue:${g}:${f.id}`:`unknown:${f.id}`,address:g?f.address.trim():"",verifiedAddress:!!g,markets:[]},c.push(x),g&&(u.has(g)||u.set(g,[]),u.get(g).push(x))),x.markets.push(f)}return c.sort((f,g)=>{const x=f.markets.map(N=>Zo(N.dates)).filter(Boolean).sort()[0]||"9999",k=g.markets.map(N=>Zo(N.dates)).filter(Boolean).sort()[0]||"9999";return x.localeCompare(k)||f.address.localeCompare(g.address,"it")})}function tl(o=new Date){const c=o.getFullYear(),u=String(o.getMonth()+1).padStart(2,"0"),f=String(o.getDate()).padStart(2,"0");return[c,u,f].join("-")}function rh(o,c=new Date){const u=tl(c);return Array.isArray(o)&&o.some(f=>typeof f=="string"&&/^\d{4}-\d{2}-\d{2}$/.test(f)&&f>=u)}function Ka(o,c,u=new Date){return rh(o,u)?c==="confermata"?"":c==="riportata"?"Date riportate dalla fonte. Controlla eventuali variazioni prima di partire.":c==="mista"?"Date previste e date riportate dalle fonti. Controlla la singola scheda e le eventuali variazioni prima di partire.":"Date previste, non confermate per ogni singola edizione. Controlla la fonte prima di partire.":"Nessuna data futura disponibile. Giorni e aperture da verificare presso la fonte prima di partire."}const Rn=o=>typeof o=="string"?o.trim():"",Ti=o=>Array.isArray(o)?o:[],ld=new Set(["calendar","recurrence","edition","occurrences","suspensions"]),Jo={source_listed:"",rescheduled:"Spostato",cancelled:"Annullato",postponed:"Rinviato"};function ir(o){if(typeof o!="string"||!/^\d{4}-\d{2}-\d{2}$/.test(o))return!1;const c=new Date(o+"T12:00:00Z");return Number.isFinite(c.getTime())&&c.toISOString().slice(0,10)===o}function Mn(o){return new Date(o+"T12:00:00").toLocaleDateString("it-IT",{day:"numeric",month:"short",year:"numeric"})}function Bc(o){try{const c=new URL(o);if(c.protocol!=="https:"||c.username||c.password||c.port||c.search||c.hash)return null;let u;if(c.host==="www.cosedicasa.com"&&(u=c.pathname.match(/^\/mercatini\/([a-z0-9]+(?:-[a-z0-9]+)*)\/?$/)))return["cosedicasa.com",u[1]];if(c.host==="www.eventiesagre.it"&&(u=c.pathname.match(/^\/(?:Mercatini|Eventi)_[A-Za-z+]+\/(\d+)_[^/]+\.html$/)))return["eventiesagre.it",u[1]]}catch{}return Xc(o)}function ad(o,c){var x;const u=o==null?void 0:o.editorialEvidence,f=Bc(u==null?void 0:u.primary_url),g=Bc(u==null?void 0:u.final_url);if(!u||u.schema!==1||u.manager!=="editorial-detail"||((x=u.market)==null?void 0:x.slug)!==(o==null?void 0:o.id)||u.primary_url!==(o==null?void 0:o.sourceUrl)||u.requested_url!==u.primary_url||!f||!g||f[0]!==u.publisher||f[1]!==u.source_id||g[0]!==f[0]||g[1]!==f[1]&&(f[0]!=="cosedicasa.com"||u.redirect_observed!==!0)||!/^[a-f0-9]{64}$/.test(u.source_sha256||"")||!Number.isInteger(u.source_bytes)||u.source_bytes<100||u.source_bytes>25e5||!ir(u.read_on)||u.read_on>c||!["limit_forecasts","reported_explicit"].includes(u.calendar_mode)||!u.facts||typeof u.facts!="object"||Array.isArray(u.facts))return null;for(const k of["published_on","modified_on"])if(u[k]&&(!ir(u[k])||u[k]>u.read_on))return null;return f[1].startsWith("citynews-")&&(u.final_url!==u.primary_url||u.canonical_url!==u.primary_url||u.redirect_observed!==!1||u.hash_basis!=="http_response_bytes"||u.modified_on||u.market.citta!==o.originalCity||u.market.provincia!==o.province||u.market.regione!==o.region)?null:u}function sd(o){return new Set(Ti(o.conflicts).flatMap(c=>c&&typeof c=="object"&&Rn(c.field)?[c.field]:typeof c=="string"&&/calendar|edition|recurrence|archive_marker_date/.test(c)?["calendar"]:[]))}function ud(o){return Ti(o.edition_intervals).filter(c=>c&&ir(c.start)&&ir(c.end)&&c.start<=c.end).slice(0,100)}function Ja(o){return Ti(o.occurrences).filter(c=>c&&ir(c.date)&&Object.hasOwn(Jo,c.status)).slice(0,600)}function ih(o,c){if(o.archive_marker===!0)return!0;const u=ud(o),f=Ja(o);return(u.length>0||f.length>0)&&u.every(g=>g.end<c)&&f.every(g=>g.date<c)}function cd(o){return new Map(Ti(o==null?void 0:o.calendarExceptions).filter(c=>c&&ir(c.data)).map(c=>[c.data,Rn(c.motivo)]))}const Wc=o=>typeof o=="string"&&/^(?:(?:[01]\d|2[0-3]):[0-5]\d|24:00)$/.test(o)?o:"";function dd(o){const c=Wc(o.start_time),u=Wc(o.end_time);return c&&u?`${c}–${u}`:c?`Dalle ${c}; chiusura non indicata per questa data`:u?`Termine alle ${u}; apertura non indicata per questa data`:"Orario del giorno non indicato"}function oh(o,c=new Date){const u=tl(c),f=ad(o,u);if(!f)return null;const g=f.facts,x=cd(o),k=sd(f),N=[...k].some(E=>ld.has(E)),F=ih(g,u),X=[];F&&X.push("La pagina descrive un’edizione passata. Le aperture attuali sono da verificare."),N?X.push("La fonte contiene indicazioni discordanti sul calendario. Le prossime aperture richiedono un riscontro."):g.calendar_complete!==!0&&X.push("Il calendario nella pagina è incompleto; non permette di ricavare tutte le prossime aperture."),k.has("hours")&&X.push("La fonte contiene orari discordanti, da verificare prima della visita."),k.has("address")&&X.push("La fonte contiene indicazioni discordanti sull’indirizzo.");const G=["conditions","hours_qualifications","scope_statements"].flatMap(E=>Ti(g[E])).map(E=>Rn(typeof E=="string"?E:E==null?void 0:E.text)).filter(Boolean);X.push(...G);const q=Ja(g),te=new Set(q.map(E=>E.date)),_=ud(g).filter(E=>E.start!==E.end||!te.has(E.start)).map(E=>{const M=[...x].filter(([Z])=>E.start<=Z&&Z<=E.end).sort(([Z],[ae])=>Z.localeCompare(ae)),K=M.map(([Z,ae])=>`${Mn(Z)}: Annullato${ae?" — "+ae:""}`);return{key:"period/"+E.start+"/"+E.end,sortDate:E.start,kind:"interval",label:E.start===E.end?Mn(E.start):`${Mn(E.start)} – ${Mn(E.end)}`,status:M.length?E.start===E.end?"Annullato":"Variazioni nel periodo":N?"Periodo da verificare":E.end<u?"Periodo passato":"Periodo riportato",hours:"",note:["Il periodo non specifica le aperture dei singoli giorni.",...K].join(" ")}});for(const E of q){const M=x.has(E.date);_.push({key:["date",E.date,E.start_time,E.end_time,E.status].join("/"),sortDate:E.date,kind:"date",label:Mn(E.date),status:M?"Annullato":Jo[E.status]||(N?"Data da verificare":g.archive_marker===!0?"Data nella pagina archiviata":E.date<u?"Data passata":"Data riportata"),hours:!M&&!N&&!k.has("hours")&&g.archive_marker!==!0&&["source_listed","rescheduled"].includes(E.status)?dd(E):"",note:[Rn(E.note),M?x.get(E.date):""].filter(Boolean).join(" · ")})}return _.sort((E,M)=>E.sortDate.localeCompare(M.sortDate)||E.key.localeCompare(M.key)),{title:F?"Edizione passata descritta dalla fonte":"Dettagli dell’edizione nella fonte",sourceName:f.publisher==="cosedicasa.com"?"Cose di Casa":f.publisher==="eventiesagre.it"?"Eventi e Sagre":`Citynews · ${f.publisher}`,sourceUrl:f.final_url,readOn:Mn(f.read_on),editorialDate:f.modified_on?`Modifica dichiarata: ${Mn(f.modified_on)}`:f.published_on?`Pubblicazione dichiarata: ${Mn(f.published_on)}`:"Data dei contenuti non dichiarata",historical:F,calendarConflict:N,notes:[...new Set(X)],rows:_,hours:k.has("hours")?"":Rn(g.hours_text),hoursLabel:F?"Orari riportati per l’edizione passata":"Orari riportati per questa edizione",recurrence:Rn(g.recurrence_text)}}function lh(o,c=new Date){const u=oh(o,c),f=u?u.historical:(o==null?void 0:o.indexHoursScope)==="storico";return{evidence:u,hours:f?"Orari attuali da verificare":!u&&!(o!=null&&o.sourceCalendar)&&(o==null?void 0:o.indexHoursScope)==="per_data"?"Vedi gli orari per data":Rn(o==null?void 0:o.hours),recurrence:f?"":Rn(o==null?void 0:o.recurrence)}}function ah(o,c,u=new Date){const f=ad(o,tl(u));if(!f)return null;if(!ir(c))return"Orario per questa data da verificare";if(cd(o).has(c))return"Annullato";const g=sd(f);if([...g].some(k=>ld.has(k))||g.has("hours")||f.facts.archive_marker===!0)return"Orario per questa data da verificare";const x=Ja(f.facts).filter(k=>k.date===c);return x.length?[...new Set(x.map(k=>Jo[k.status]&&k.status!=="rescheduled"?Jo[k.status]:dd(k)))].join(" · "):"Orario per questa data non indicato"}const Di=new Set(["source_listed","rescheduled"]),rr={source_listed:"",cancelled:"Annullato",postponed:"Rinviato",rescheduled:"Spostato"},_t=o=>typeof o=="string"?o.trim():"",Rr=o=>typeof o=="string"&&/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(o)?o:"";function Or(o){if(typeof o!="string"||!/^\d{4}-\d{2}-\d{2}$/.test(o))return!1;const c=new Date(o+"T12:00:00Z");return Number.isFinite(c.getTime())&&c.toISOString().slice(0,10)===o}function Fn(o){return Or(o)?new Date(o+"T12:00:00").toLocaleDateString("it-IT",{weekday:"short",day:"numeric",month:"short",year:"numeric"}):"Data da verificare"}function fd(o){const c=Rr(o.start_time),u=Rr(o.end_time);return c&&u?`${c}–${u}`:c?`Dalle ${c}; chiusura non indicata per questa data`:u?`Termine alle ${u}; apertura non indicata per questa data`:"Orario del giorno non indicato"}function pd(o,c){return!o||!Array.isArray(o.occorrenze)?[]:o.occorrenze.filter(u=>u&&Or(u.date)&&u.date>=c&&Object.hasOwn(rr,u.status))}function hd(o,c){const u=new Map;for(const f of Array.isArray(o==null?void 0:o.calendarExceptions)?o.calendarExceptions:[]){if(!f||!Or(f.data)||f.data<c)continue;const g=u.get(f.data)||[];_t(f.motivo)&&!g.includes(_t(f.motivo))&&g.push(_t(f.motivo)),u.set(f.data,g)}return u}const Hc=o=>o.interval_start+"/"+o.interval_end;function sh(o,c=new Date){var te;const u=o==null?void 0:o.sourceCalendar,f=((te=o==null?void 0:o.sourceDetail)==null?void 0:te.evento)||{},g=tl(c),x=hd(o,g),k=(Array.isArray(u==null?void 0:u.intervalli)?u.intervalli:[]).filter(_=>_&&Or(_.start)&&Or(_.end)&&_.start<=_.end&&_.end>=g&&_.hours_scope==="interval_boundaries"&&_.continuous_opening_confirmed===!1&&Object.hasOwn(rr,_.status||"source_listed")),N=new Set(k.map(_=>_.start+"/"+_.end)),F=pd(u,g).map(_=>x.has(_.date)?{..._,status:"cancelled",note:[...new Set([_t(_.note),...x.get(_.date)])].filter(Boolean).join(" · ")}:_),X=F.filter(_=>!N.has(Hc(_))).map(_=>({key:[_.date,_.start_time,_.end_time,_.status].join("/"),sortDate:_.date,label:Fn(_.date),hours:Di.has(_.status)?fd(_):"",status:rr[_.status],note:_t(_.note),kind:"date"}));for(const _ of k){const E=_.status||"source_listed",M=new Map;for(const Z of F.filter(ae=>Hc(ae)===_.start+"/"+_.end))(Z.status!==E||x.has(Z.date))&&M.set(Z.date,`${Fn(Z.date)}: ${rr[Z.status]||"Riportato dalla fonte"}${_t(Z.note)?" — "+_t(Z.note):""}`);for(const[Z,ae]of x)_.start<=Z&&Z<=_.end&&!M.has(Z)&&M.set(Z,`${Fn(Z)}: Annullato${ae.length?" — "+ae.join(" · "):""}`);const K=[];Rr(_.start_time)&&K.push(`Inizio ${Fn(_.start)}, ore ${_.start_time}`),Rr(_.end_time)&&K.push(`Termine ${Fn(_.end)}, ore ${_.end_time}`),X.push({key:_.start+"/"+_.end,sortDate:_.start,label:`${Fn(_.start)} – ${Fn(_.end)}`,hours:Di.has(E)?K.join("; ")||"Orari del periodo non indicati":"",status:rr[E]||(M.size?"Variazioni nel periodo":""),kind:"interval",note:[Di.has(E)?"Il periodo è riportato dalla fonte. Aperture e orari dei singoli giorni da verificare.":"",...[...M].sort(([Z],[ae])=>Z.localeCompare(ae)).map(([,Z])=>Z)].filter(Boolean).join(" ")})}for(const[_,E]of x)F.some(M=>M.date===_)||k.some(M=>M.start<=_&&_<=M.end)||X.push({key:_+"/exception",sortDate:_,label:Fn(_),hours:"",status:"Annullato",note:E.join(" · "),kind:"date"});X.sort((_,E)=>_.sortDate.localeCompare(E.sortDate)||_.key.localeCompare(E.key));const G=[...new Set(["conditions","calendar_notes","hours_qualifications"].flatMap(_=>Array.isArray(f[_])?f[_]:[]).map(_t).filter(_=>_&&!_t(o==null?void 0:o.hours).includes(_)))];(u==null?void 0:u.ambito_calendario)==="schema_occurrence_only"&&G.push("La fonte riporta questa singola edizione. Altri appuntamenti non sono disponibili nel calendario letto.");const q=X.some(_=>_.kind==="interval"||_.note||_.status)||new Set(X.map(_=>_.hours)).size>1;return{rows:X,notes:G,hasVariations:q}}function Ya(o,c){if(hd(o,c).has(c))return"Annullato";if(!(o!=null&&o.sourceCalendar)){const f=ah(o,c);return f!==null?f:(o==null?void 0:o.indexHoursScope)==="storico"?"Orari attuali da verificare":(o==null?void 0:o.indexHoursScope)==="per_data"?"Vedi gli orari per data":_t(o==null?void 0:o.hours)||"Orario da verificare"}if(!Or(c))return _t(o==null?void 0:o.hours)||"Orario da verificare";const u=pd(o.sourceCalendar,c).filter(f=>f.date===c);return u.length?[...new Set(u.map(f=>{if(!Di.has(f.status))return rr[f.status];if(f.interval_start||f.interval_end){const g=(o.sourceCalendar.intervalli||[]).find(x=>x.start===f.interval_start&&x.end===f.interval_end);return g&&g.status&&!Di.has(g.status)?rr[g.status]||"Stato da verificare":f.date===f.interval_start&&Rr(f.start_time)?`Inizio del periodo alle ${f.start_time}`:f.date===f.interval_end&&Rr(f.end_time)?`Termine del periodo alle ${f.end_time}`:"Orario del singolo giorno da verificare"}return fd(f)}))].join(" · "):"Orario per questa data non indicato"}function Qc(o){try{const c=new URL(o);return["https:","http:"].includes(c.protocol)&&!c.username&&!c.password?c.href:""}catch{return""}}function uh(o){const c=(o==null?void 0:o.evento)||{},u=c.organizer&&_t(c.organizer.name)?{label:c.organizer.name,href:Qc(c.organizer.url)}:null,f=(Array.isArray(c.contacts)?c.contacts:[]).flatMap(g=>{const x=_t(g==null?void 0:g.value);if((g==null?void 0:g.kind)==="email"&&/^[^\s?@]+@[^\s?@]+\.[^\s?@]+$/.test(x))return[{label:x,href:"mailto:"+x}];if((g==null?void 0:g.kind)==="telephone"&&/^[+\d() .-]{5,40}$/.test(x)&&/\d/.test(x))return[{label:x,href:"tel:"+x.replace(/[() .-]/g,"")}];const k=(g==null?void 0:g.kind)==="website"?Qc(x):"";return k?[{label:"Sito indicato dalla fonte",href:k}]:[]});return{organizer:u,links:f}}function Ba(o){return o?new Date(o+"T12:00:00").toLocaleDateString("it-IT",{weekday:"short",day:"numeric",month:"short"}):"Data da verificare"}function ch({group:o,loadMarket:c,onOpenMarket:u,selectedWeekday:f=null,autoExpand:g=!1}){const x=U.useId(),[k,N]=U.useState(g),[F,X]=U.useState({}),[G,q]=U.useState(!1),[te,_]=U.useState(""),[E,M]=U.useState(!1),[K,Z]=U.useState({}),ae=o.markets.map(H=>H.id).join("|");U.useEffect(()=>{g&&N(!0)},[g]),U.useEffect(()=>{if(!k)return;const H=o.markets.filter(ne=>!F[ne.id]);if(!H.length)return;let B=!1;return q(!0),_(""),Promise.allSettled(H.map(ne=>c(ne.id))).then(ne=>{if(B)return;const se={};let ye=0;ne.forEach((ie,T)=>{ie.status==="fulfilled"&&ie.value?se[H[T].id]=ie.value:(se[H[T].id]=H[T],ye++)}),X(ie=>({...ie,...se})),ye&&_("Alcune sedi non sono disponibili nei dettagli: riprova più tardi."),q(!1)}),()=>{B=!0}},[k,ae,c]);const ze=U.useMemo(()=>eh(o.markets),[o.markets]),pe=U.useMemo(()=>o.markets.map(H=>Zo(H.dates||[],f)).filter(Boolean).sort()[0]||null,[o.markets,f]),Me=U.useMemo(()=>k?nh(o.markets.map(H=>F[H.id]||H)):[],[o.markets,F,k]),he=Me.filter(H=>H.verifiedAddress),_e=Me.filter(H=>!H.verifiedAddress),Ue=[...he,...E||he.length===0?_e:[]],He=o.markets.some(H=>H.dateQuality==="riportata"),qe=o.markets.some(H=>!["confermata","riportata"].includes(H.dateQuality)),nt=Ka(o.markets.flatMap(H=>H.dates||[]),He&&qe?"mista":He?"riportata":qe?"prevista":"confermata");return a.jsxs("article",{className:"weekly-city-card","data-testid":"weekly-city-group","aria-label":`Mercati settimanali a ${o.city}`,children:[a.jsxs("div",{className:"weekly-city-top",children:[a.jsxs("span",{className:"weekly-city-overline",children:["Mercati settimanali · ",o.city]}),a.jsxs("span",{className:"weekly-city-counter",children:[o.markets.length," schede"]})]}),a.jsxs("h2",{className:"weekly-city-heading",children:["Mercati settimanali a ",o.city]}),a.jsxs("div",{className:"weekly-city-subtitle",children:[a.jsx("span",{children:ze.length?`${ze.length} ${ze.length===1?"giornata":"giornate"} della settimana`:"Calendario da verificare"}),pe&&a.jsxs("span",{children:["Prossimo: ",Ba(pe)]})]}),a.jsx("div",{className:"weekly-day-chips","aria-label":"Giorni registrati",children:ze.map(H=>a.jsx("span",{className:f===H?"weekly-day-chip highlighted":"weekly-day-chip",children:id[H]},H))}),nt&&a.jsx("p",{className:"weekly-city-caution",children:nt}),a.jsxs("button",{type:"button",className:"weekly-city-toggle","aria-controls":x,"aria-expanded":k,onClick:()=>N(H=>!H),children:[a.jsx("span",{children:k?"Nascondi sedi e giornate":"Visualizza sedi e giornate"}),a.jsx("span",{"aria-hidden":"true",className:k?"weekly-chevron open":"weekly-chevron",children:"⌄"})]}),k&&a.jsxs("div",{id:x,className:"weekly-city-panel",children:[G&&a.jsx("div",{className:"weekly-load",role:"status",children:"Caricamento sedi…"}),te&&a.jsx("p",{className:"weekly-city-caution",role:"alert",children:te}),!G&&Me.length>0&&a.jsxs(a.Fragment,{children:[a.jsxs("p",{className:"weekly-venue-total",children:[he.length," ",he.length===1?"sede riportata":"sedi riportate",_e.length>0&&` · ${_e.length} ${_e.length===1?"scheda":"schede"} senza indirizzo`,". Ogni scheda e fonte resta accessibile. Le segnalazioni identiche sono raggruppate solo nella visualizzazione."]}),_e.length>0&&he.length>0&&a.jsxs("button",{type:"button",className:"weekly-unknown-toggle","aria-expanded":E,onClick:()=>M(H=>!H),children:[E?"Nascondi":"Mostra",` ${_e.length} ${_e.length===1?"appuntamento":"appuntamenti"} senza sede identificata`]}),Ue.map((H,B)=>a.jsxs("section",{className:"weekly-venue","data-known":H.verifiedAddress?"true":"false","aria-label":H.address||"Sede da verificare",children:[a.jsxs("div",{className:"weekly-venue-title-row",children:[a.jsx("span",{className:"weekly-venue-index",children:B+1}),a.jsxs("div",{children:[a.jsx("h3",{className:"weekly-venue-title",children:H.address||"Sede da verificare"}),!H.verifiedAddress&&a.jsx("p",{className:"weekly-venue-note",children:"Indirizzo assente o troppo generico: non unito ad altre sedi"}),H.markets.some(ne=>Fr(ne).length>0)&&a.jsx("p",{className:"weekly-venue-note",role:"note",children:"Una o più schede riportano un indirizzo salvato discordante con la fonte. Apri la scheda per confrontare le sedi."})]})]}),a.jsx("div",{className:"weekly-appointment-list",children:Jp(H.markets).map(ne=>{const se=ne.market,ye=Zo(se.dates||[],f),ie=!!K[ne.key],T=Fr(se).length>0;return a.jsxs("div",{className:"weekly-appointment-group",children:[a.jsxs("button",{type:"button",className:"weekly-appointment",onClick:()=>u(se),"aria-label":"Apri "+Ba(ye)+", "+(H.address||o.city),children:[a.jsx("span",{className:"weekly-appointment-date",children:Ba(ye)}),a.jsxs("span",{className:"weekly-appointment-meta",children:[Ya(se,ye),se.dateQuality!=="confermata"&&a.jsx("small",{children:se.dateQuality==="riportata"?" · Riportato dalla fonte":" · Previsto"}),T&&a.jsx("small",{className:"weekly-address-caution",children:"Indirizzo salvato discordante con la fonte"})]}),a.jsx("span",{"aria-hidden":"true",className:"weekly-appointment-arrow",children:"›"})]}),ne.records.length>1&&a.jsxs(a.Fragment,{children:[a.jsxs("button",{type:"button",className:"weekly-duplicate-toggle","aria-expanded":ie,onClick:()=>Z(A=>({...A,[ne.key]:!A[ne.key]})),children:[ne.records.length," schede della stessa fonte"," · ",ie?"Nascondi originali":"Mostra originali"]}),ie&&a.jsx("div",{className:"weekly-duplicate-records",children:ne.records.map(A=>a.jsxs("button",{type:"button",className:"weekly-original-record",onClick:()=>u(A),children:[A.name," · ",A.hours||"Orario da verificare",Fr(A).length>0&&a.jsx("small",{children:" · Indirizzo salvato discordante con la fonte"}),a.jsx("span",{"aria-hidden":"true",children:"›"})]},A.id))})]})]},ne.key)})})]},H.key))]})]})]})}function Kc(o,c){var g;if(!o||o.locationReviewRequired||Fr(o,c).length)return null;if(o.positionQuality==="precisa"&&Number.isFinite(o.lat)&&Number.isFinite(o.lng))return o.lat+","+o.lng;const u=((g=o.address)==null?void 0:g.trim())||"",f=/\b(via|viale|piazza|piazzale|piazzetta|corso|largo|vicolo|strada|contrada|lungomare|località|localita|borgo|parco)\b/i;return u.length>=9&&f.test(u)?[o.name,u,o.city,"Italia"].filter(Boolean).join(", "):null}function dh(o,c="",u=!1){return typeof c=="string"&&c.trim()&&!u?null:o||null}const fh=U.lazy(()=>fp(()=>import("./MarketsMap-DocHHfX7.js"),__vite__mapDeps([0,1]),import.meta.url)),ph=["Alimentare","Antiquariato","Vintage e abbigliamento","Usato","Artigianato","Misto"],hh=[],gh=[],mh={Alimentare:"🍅",Antiquariato:"🏺","Vintage e abbigliamento":"👗",Usato:"📦",Artigianato:"🎨",Misto:"🎪"},vh={Alimentare:"#446E47",Antiquariato:"#B94439","Vintage e abbigliamento":"#705073",Usato:"#805B08",Artigianato:"#216886",Misto:"#9C4B36"};function dn(o=new Date){return[o.getFullYear(),String(o.getMonth()+1).padStart(2,"0"),String(o.getDate()).padStart(2,"0")].join("-")}const Xo=new Date,ji=dn(Xo);function Wa(o){if(!o)return"Data da verificare";const c=new Date(o+"T00:00:00");return Number.isNaN(c.getTime())?"Data da verificare":c.toLocaleDateString("it-IT",{weekday:"short",day:"numeric",month:"short"})}function yh(o=[],c="prevista"){const u=c==="confermata",f=u?"":" · da verificare",g=new Date,x=dn(g),k=new Date(g);k.setDate(k.getDate()+1);const N=new Date(g);N.setDate(N.getDate()+(6-g.getDay()+7)%7);const F=new Date(N);return F.setDate(F.getDate()+1),o.includes(x)?{label:"Oggi"+f,color:u?"#B94439":"#81796D"}:o.includes(dn(k))?{label:"Domani"+f,color:u?"#B94439":"#81796D"}:o.includes(dn(N))||o.includes(dn(F))?{label:"Weekend"+f,color:u?"#446E47":"#81796D"}:null}function zi(o=[]){return o.filter(c=>c>=dn()).sort()[0]||null}const ke=({name:o,size:c=20,color:u="currentColor",strokeWidth:f=1.8})=>{const g={search:a.jsxs(a.Fragment,{children:[a.jsx("circle",{cx:"11",cy:"11",r:"8"}),a.jsx("line",{x1:"21",y1:"21",x2:"16.65",y2:"16.65"})]}),filter:a.jsx(a.Fragment,{children:a.jsx("polygon",{points:"22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"})}),heart:a.jsx("path",{d:"M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"}),heartFilled:a.jsx("path",{d:"M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z",fill:"currentColor"}),mapPin:a.jsxs(a.Fragment,{children:[a.jsx("path",{d:"M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"}),a.jsx("circle",{cx:"12",cy:"10",r:"3"})]}),clock:a.jsxs(a.Fragment,{children:[a.jsx("circle",{cx:"12",cy:"12",r:"10"}),a.jsx("polyline",{points:"12 6 12 12 16 14"})]}),compass:a.jsxs(a.Fragment,{children:[a.jsx("circle",{cx:"12",cy:"12",r:"10"}),a.jsx("polygon",{points:"16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"})]}),bell:a.jsxs(a.Fragment,{children:[a.jsx("path",{d:"M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"}),a.jsx("path",{d:"M13.73 21a2 2 0 0 1-3.46 0"})]}),settings:a.jsxs(a.Fragment,{children:[a.jsx("circle",{cx:"12",cy:"12",r:"3"}),a.jsx("path",{d:"M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"})]}),chevronLeft:a.jsx("polyline",{points:"15 18 9 12 15 6"}),chevronRight:a.jsx("polyline",{points:"9 18 15 12 9 6"}),x:a.jsxs(a.Fragment,{children:[a.jsx("line",{x1:"18",y1:"6",x2:"6",y2:"18"}),a.jsx("line",{x1:"6",y1:"6",x2:"18",y2:"18"})]}),copy:a.jsxs(a.Fragment,{children:[a.jsx("rect",{x:"9",y:"9",width:"13",height:"13",rx:"2",ry:"2"}),a.jsx("path",{d:"M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"})]}),navigation:a.jsx("polygon",{points:"3 11 22 2 13 21 11 13 3 11"}),share:a.jsxs(a.Fragment,{children:[a.jsx("circle",{cx:"18",cy:"5",r:"3"}),a.jsx("circle",{cx:"6",cy:"12",r:"3"}),a.jsx("circle",{cx:"18",cy:"19",r:"3"}),a.jsx("line",{x1:"8.59",y1:"13.51",x2:"15.42",y2:"17.49"}),a.jsx("line",{x1:"15.41",y1:"6.51",x2:"8.59",y2:"10.49"})]}),calendar:a.jsxs(a.Fragment,{children:[a.jsx("rect",{x:"3",y:"4",width:"18",height:"18",rx:"2",ry:"2"}),a.jsx("line",{x1:"16",y1:"2",x2:"16",y2:"6"}),a.jsx("line",{x1:"8",y1:"2",x2:"8",y2:"6"}),a.jsx("line",{x1:"3",y1:"10",x2:"21",y2:"10"})]}),list:a.jsxs(a.Fragment,{children:[a.jsx("line",{x1:"8",y1:"6",x2:"21",y2:"6"}),a.jsx("line",{x1:"8",y1:"12",x2:"21",y2:"12"}),a.jsx("line",{x1:"8",y1:"18",x2:"21",y2:"18"}),a.jsx("line",{x1:"3",y1:"6",x2:"3.01",y2:"6"}),a.jsx("line",{x1:"3",y1:"12",x2:"3.01",y2:"12"}),a.jsx("line",{x1:"3",y1:"18",x2:"3.01",y2:"18"})]}),map:a.jsxs(a.Fragment,{children:[a.jsx("polygon",{points:"1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"}),a.jsx("line",{x1:"8",y1:"2",x2:"8",y2:"18"}),a.jsx("line",{x1:"16",y1:"6",x2:"16",y2:"22"})]}),check:a.jsx("polyline",{points:"20 6 9 17 4 12"}),minus:a.jsx("line",{x1:"5",y1:"12",x2:"19",y2:"12"}),plus:a.jsxs(a.Fragment,{children:[a.jsx("line",{x1:"12",y1:"5",x2:"12",y2:"19"}),a.jsx("line",{x1:"5",y1:"12",x2:"19",y2:"12"})]}),externalLink:a.jsxs(a.Fragment,{children:[a.jsx("path",{d:"M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"}),a.jsx("polyline",{points:"15 3 21 3 21 9"}),a.jsx("line",{x1:"10",y1:"14",x2:"21",y2:"3"})]}),info:a.jsxs(a.Fragment,{children:[a.jsx("circle",{cx:"12",cy:"12",r:"10"}),a.jsx("line",{x1:"12",y1:"16",x2:"12",y2:"12"}),a.jsx("line",{x1:"12",y1:"8",x2:"12.01",y2:"8"})]}),sort:a.jsxs(a.Fragment,{children:[a.jsx("line",{x1:"12",y1:"5",x2:"12",y2:"19"}),a.jsx("polyline",{points:"19 12 12 19 5 12"})]}),bookmark:a.jsx("path",{d:"M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"})};return a.jsx("svg",{width:c,height:c,viewBox:"0 0 24 24",fill:"none",stroke:u,strokeWidth:f,strokeLinecap:"round",strokeLinejoin:"round",style:{flexShrink:0},children:g[o]})},xh=`
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Source+Sans+3:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

:root {
  --terracotta: #B94439;
  --terracotta-light: #E8857D;
  --olive: #446E47;
  --olive-light: #7FA882;
  --olive-pale: #E8F0E9;
  --beige: #F5F0E8;
  --beige-dark: #E8E0D4;
  --sand: #D4C5A9;
  --ink: #2C2416;
  --ink-light: #5C513F;
  --ink-lighter: #6C6255;
  --cream: #FDFBF7;
  --white: #FFFFFF;
  --shadow-sm: 0 1px 3px rgba(44,36,22,0.06);
  --shadow-md: 0 4px 12px rgba(44,36,22,0.08);
  --shadow-lg: 0 8px 30px rgba(44,36,22,0.12);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --font-display: 'DM Serif Display', Georgia, serif;
  --font-body: 'Source Sans 3', -apple-system, sans-serif;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-body);
  background: var(--beige);
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
}

/* Animations */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
@keyframes slideInRight {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
@keyframes heartPop {
  0% { transform: scale(1); }
  50% { transform: scale(1.3); }
  100% { transform: scale(1); }
}
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(199,81,70,0.3); }
  50% { box-shadow: 0 0 0 8px rgba(199,81,70,0); }
}

.app-container {
  max-width: 480px;
  margin: 0 auto;
  min-height: 100vh;
  background: var(--cream);
  position: relative;
  overflow: hidden;
}

/* ─── Header ─── */
.header {
  background: linear-gradient(180deg, var(--cream) 0%, var(--cream) 90%, transparent 100%);
  padding: 16px 20px 8px;
  position: sticky;
  top: 0;
  z-index: 50;
  backdrop-filter: blur(12px);
}

.header-title {
  font-family: var(--font-display);
  font-size: 28px;
  color: var(--ink);
  letter-spacing: -0.3px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title .accent {
  color: var(--terracotta);
}

/* ─── Search ─── */
.search-container {
  position: relative;
  margin-bottom: 12px;
}

.search-input {
  width: 100%;
  padding: 12px 16px 12px 44px;
  border: 2px solid var(--beige-dark);
  border-radius: var(--radius-lg);
  font-family: var(--font-body);
  font-size: 15px;
  color: var(--ink);
  background: var(--white);
  transition: all 0.25s ease;
  outline: none;
}

.search-input:focus {
  border-color: var(--olive);
  box-shadow: 0 0 0 3px var(--olive-pale);
}

.search-input::placeholder {
  color: var(--ink-lighter);
}

.search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--ink-lighter);
}

/* ─── Quick Chips ─── */
.chips-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  scrollbar-width: none;
  padding: 4px 0 8px;
  -webkit-overflow-scrolling: touch;
}

.chips-row::-webkit-scrollbar { display: none; }

.chip {
  white-space: nowrap;
  padding: 8px 16px;
  border-radius: 100px;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  border: 1.5px solid var(--beige-dark);
  background: var(--white);
  color: var(--ink-light);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.chip:hover {
  border-color: var(--sand);
  background: var(--beige);
}

.chip.active {
  background: var(--ink);
  color: var(--cream);
  border-color: var(--ink);
}

/* ─── Controls Row ─── */
.controls-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 0 12px;
}

.view-toggle {
  display: flex;
  background: var(--beige);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 2px;
}

.view-toggle button {
  padding: 7px 14px;
  border: none;
  border-radius: 6px;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-lighter);
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all 0.2s ease;
}

.view-toggle button.active {
  background: var(--white);
  color: var(--ink);
  box-shadow: var(--shadow-sm);
}

.filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-light);
  background: var(--white);
  cursor: pointer;
  transition: all 0.2s ease;
  margin-left: auto;
}

.filter-btn:hover { border-color: var(--sand); }

.filter-btn.has-filters {
  background: var(--ink);
  color: var(--cream);
  border-color: var(--ink);
}

.filter-count {
  background: var(--terracotta);
  color: white;
  font-size: 11px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.sort-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 12px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-light);
  background: var(--white);
  cursor: pointer;
  transition: all 0.2s;
}

/* ─── Market Cards ─── */
.markets-list {
  padding: 0 20px 100px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.market-card {
  background: var(--white);
  border-radius: var(--radius-lg);
  padding: 16px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all 0.25s ease;
  animation: fadeInUp 0.4s ease both;
  border: 1px solid rgba(44,36,22,0.04);
  position: relative;
  overflow: hidden;
}

.market-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
.market-card-open {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  cursor: pointer;
  border: 0;
  background: transparent;
  border-radius: inherit;
}
.market-card-open:focus-visible {
  outline: 3px solid var(--olive);
  outline-offset: -3px;
}


.market-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 4px 0 0 4px;
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 8px;
}

.card-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.category-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.date-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 100px;
  font-size: 11px;
  font-weight: 600;
  color: white;
  letter-spacing: 0.02em;
}

.fav-btn {
  position: relative;
  z-index: 2;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  transition: all 0.2s;
  color: var(--ink-lighter);
  flex-shrink: 0;
}

.fav-btn:hover { color: var(--terracotta); }
.fav-btn.active { color: var(--terracotta); animation: heartPop 0.35s ease; }

.card-name {
  font-family: var(--font-display);
  font-size: 18px;
  color: var(--ink);
  margin-bottom: 6px;
  line-height: 1.25;
}

.card-info {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  font-size: 13px;
  color: var(--ink-light);
}

.card-info-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.card-distance {
  color: var(--olive);
  font-weight: 600;
}

/* ─── Map View ─── */
.map-container {
  position: relative;
  height: calc(100vh - 260px);
  background: var(--beige);
  margin: 0 20px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.map-svg {
  width: 100%;
  height: 100%;
}

.map-pin {
  cursor: pointer;
  transition: all 0.2s ease;
}

.map-pin:hover {
  transform: scale(1.15);
}

.map-tooltip {
  position: absolute;
  background: var(--white);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  box-shadow: var(--shadow-lg);
  z-index: 20;
  min-width: 220px;
  max-width: 280px;
  animation: scaleIn 0.2s ease;
  border: 1px solid rgba(44,36,22,0.06);
}

.tooltip-name {
  font-family: var(--font-display);
  font-size: 16px;
  margin-bottom: 6px;
}

.tooltip-meta {
  font-size: 13px;
  color: var(--ink-light);
  margin-bottom: 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.tooltip-actions {
  display: flex;
  gap: 8px;
}

.tooltip-actions button {
  flex: 1;
  padding: 8px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 600;
  background: var(--white);
  color: var(--ink);
  cursor: pointer;
  transition: all 0.15s;
}

.tooltip-actions button:hover {
  background: var(--beige);
}

.tooltip-actions button.primary {
  background: var(--terracotta);
  color: white;
  border-color: var(--terracotta);
}

/* ─── Detail Page ─── */
.detail-page {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: var(--cream);
  overflow-y: auto;
  animation: slideUp 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.detail-hero {
  position: relative;
  padding: 60px 24px 32px;
  background: linear-gradient(135deg, var(--beige) 0%, var(--beige-dark) 100%);
  overflow: hidden;
}

.detail-hero::before {
  content: '';
  position: absolute;
  top: -50px;
  right: -50px;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  opacity: 0.06;
}

.detail-back {
  position: absolute;
  top: 16px;
  left: 16px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--white);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
  color: var(--ink);
  transition: all 0.2s;
  z-index: 5;
}

.detail-back:hover { box-shadow: var(--shadow-md); }

.detail-actions-top {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  gap: 8px;
  z-index: 5;
}

.detail-icon-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--white);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s;
  color: var(--ink-light);
}

.detail-icon-btn:hover { box-shadow: var(--shadow-md); }
.detail-icon-btn.fav-active { color: var(--terracotta); }

.detail-category-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 14px;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
}

.detail-name {
  font-family: var(--font-display);
  font-size: 30px;
  line-height: 1.15;
  color: var(--ink);
  margin-bottom: 8px;
}

.detail-city {
  font-size: 15px;
  color: var(--ink-light);
  font-weight: 500;
}

.detail-body {
  padding: 24px;
}

.detail-section {
  margin-bottom: 24px;
  animation: fadeInUp 0.4s ease both;
}

.detail-section-title {
  font-family: var(--font-display);
  font-size: 17px;
  color: var(--ink);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-dates-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.date-chip {
  padding: 6px 14px;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 500;
  background: var(--beige);
  color: var(--ink-light);
  border: 1px solid var(--beige-dark);
}

.date-chip.today {
  background: var(--terracotta);
  color: white;
  border-color: var(--terracotta);
}

.date-chip.weekend {
  background: var(--olive);
  color: white;
  border-color: var(--olive);
}

.detail-hours {
  font-size: 22px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -0.02em;
  white-space: pre-line;
  line-height: 1.5;
}

.source-calendar {
  margin-top: 14px;
  font-size: 13px;
  line-height: 1.5;
}

.source-calendar summary {
  cursor: pointer;
  font-weight: 600;
  padding: 8px 0;
}

.source-calendar-row {
  display: grid;
  grid-template-columns: minmax(100px, 0.85fr) minmax(0, 1.15fr);
  gap: 8px 14px;
  padding: 10px 0;
  border-top: 1px solid var(--beige-dark);
}

.source-calendar-row[data-period="true"] { display: block; }
.source-calendar-row dt { font-weight: 600; }
.source-calendar-row dd { margin: 0; overflow-wrap: anywhere; }
.source-calendar-note {
  font-size: 12px;
  color: var(--ink-lighter);
  margin-top: 6px;
  line-height: 1.5;
}

.detail-recurrence {
  font-size: 14px;
  color: var(--ink-lighter);
  margin-top: 4px;
}

.detail-address {
  font-size: 15px;
  color: var(--ink-light);
  line-height: 1.5;
  margin-bottom: 12px;
}

.detail-address-actions {
  display: flex;
  gap: 8px;
}

.detail-address-actions button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 11px 16px;
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.detail-address-actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--beige);
  color: var(--ink-lighter);
  border: 1px solid var(--beige-dark);
}


.btn-primary {
  background: var(--terracotta);
  color: white;
  border: none;
}
.btn-primary:hover { background: #b5443a; }

.btn-secondary {
  background: var(--white);
  color: var(--ink);
  border: 1.5px solid var(--beige-dark);
}
.btn-secondary:hover { background: var(--beige); }

.detail-description {
  font-size: 15px;
  line-height: 1.7;
  color: var(--ink-light);
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.detail-tag {
  padding: 5px 12px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 500;
  background: var(--beige);
  color: var(--ink-light);
  border: 1px solid var(--beige-dark);
}

.detail-provenance {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--beige);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--ink-lighter);
}

.confidence-bar {
  height: 4px;
  background: var(--beige-dark);
  border-radius: 2px;
  width: 60px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

/* ─── Mini Map in Detail ─── */
.detail-minimap {
  width: 100%;
  height: 140px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--beige);
  margin-bottom: 12px;
  position: relative;
}

/* ─── Filter Panel ─── */
.filter-overlay {
  position: fixed;
  inset: 0;
  background: rgba(44,36,22,0.4);
  backdrop-filter: blur(4px);
  z-index: 80;
  animation: fadeIn 0.2s ease;
}

.filter-panel {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  max-height: 85vh;
  background: var(--cream);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  z-index: 85;
  overflow-y: auto;
  animation: slideUp 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 -4px 30px rgba(44,36,22,0.15);
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 12px;
  position: sticky;
  top: 0;
  background: var(--cream);
  z-index: 5;
  border-bottom: 1px solid var(--beige-dark);
}

.filter-title {
  font-family: var(--font-display);
  font-size: 22px;
}

.filter-close {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--beige);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-light);
  transition: all 0.2s;
}

.filter-body {
  padding: 20px 24px;
}

.filter-section {
  margin-bottom: 24px;
}

.filter-section-label {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-lighter);
  margin-bottom: 10px;
}

.filter-categories {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-cat-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 14px;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 500;
  border: 1.5px solid var(--beige-dark);
  background: var(--white);
  color: var(--ink-light);
  cursor: pointer;
  transition: all 0.2s;
}

.filter-cat-chip.active {
  border-color: currentColor;
  font-weight: 600;
}

.filter-select {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 14px;
  color: var(--ink);
  background: var(--white);
  appearance: none;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}

.filter-select:focus { border-color: var(--olive); }

.range-container {
  padding: 8px 0;
}

.range-label {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--ink-light);
  margin-bottom: 8px;
}

.range-value {
  font-weight: 700;
  color: var(--ink);
}

.range-input {
  width: 100%;
  -webkit-appearance: none;
  height: 6px;
  border-radius: 3px;
  background: var(--beige-dark);
  outline: none;
}

.range-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--terracotta);
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(199,81,70,0.3);
  transition: transform 0.15s;
}

.range-input::-webkit-slider-thumb:hover {
  transform: scale(1.15);
}

.filter-footer {
  display: flex;
  gap: 10px;
  padding: 16px 24px 28px;
  border-top: 1px solid var(--beige-dark);
  position: sticky;
  bottom: 0;
  background: var(--cream);
}

.filter-footer button {
  flex: 1;
  padding: 13px;
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-reset {
  background: var(--beige);
  color: var(--ink-light);
  border: 1.5px solid var(--beige-dark);
}

.filter-apply {
  background: var(--terracotta);
  color: white;
  border: none;
}

.filter-apply:hover { background: #b5443a; }

/* ─── Sorting Dropdown ─── */
.sort-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 60;
  overflow: hidden;
  min-width: 180px;
  animation: scaleIn 0.15s ease;
  border: 1px solid rgba(44,36,22,0.06);
}

.sort-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  font-size: 14px;
  color: var(--ink-light);
  cursor: pointer;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
  font-family: var(--font-body);
  transition: background 0.15s;
}

.sort-option:hover { background: var(--beige); }
.sort-option.active { color: var(--terracotta); font-weight: 600; }

/* ─── Bottom Tabs ─── */
.bottom-tabs {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  background: var(--white);
  border-top: 1px solid var(--beige-dark);
  display: flex;
  padding: 6px 8px 22px;
  z-index: 70;
  backdrop-filter: blur(12px);
}

.tab-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 8px 4px;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--ink-lighter);
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 500;
  transition: color 0.2s;
  position: relative;
}

.tab-btn.active {
  color: var(--terracotta);
}

.tab-btn.active::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 24px;
  height: 3px;
  border-radius: 0 0 3px 3px;
  background: var(--terracotta);
}

/* ─── Favorites Page ─── */
.page-content {
  padding: 0 20px 100px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  animation: fadeIn 0.4s ease;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.4;
}

.empty-title {
  font-family: var(--font-display);
  font-size: 20px;
  color: var(--ink);
  margin-bottom: 8px;
}

.empty-text {
  font-size: 14px;
  color: var(--ink-lighter);
  line-height: 1.5;
}

/* ─── Notifications / Settings ─── */
.setting-card {
  background: var(--white);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
  border: 1px solid rgba(44,36,22,0.04);
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.setting-label {
  font-size: 15px;
  font-weight: 500;
  color: var(--ink);
}

.setting-sublabel {
  font-size: 13px;
  color: var(--ink-lighter);
  margin-top: 2px;
}

/* Toggle Switch */
.toggle {
  position: relative;
  width: 48px;
  height: 28px;
  flex-shrink: 0;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-track {
  position: absolute;
  inset: 0;
  background: var(--beige-dark);
  border-radius: 14px;
  cursor: pointer;
  transition: background 0.25s;
}

.toggle input:checked + .toggle-track {
  background: var(--olive);
}

.toggle-track::after {
  content: '';
  position: absolute;
  left: 3px;
  top: 3px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--white);
  box-shadow: 0 1px 4px rgba(0,0,0,0.15);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.toggle input:checked + .toggle-track::after {
  transform: translateX(20px);
}

/* ─── Location Selection ─── */
.location-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 16px;
}

.location-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-md);
  background: var(--white);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
  transition: all 0.2s;
}

.location-option:hover { border-color: var(--sand); }
.location-option.active {
  border-color: var(--olive);
  background: var(--olive-pale);
}

.location-option .icon-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--beige);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-light);
}

.manual-city-input {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  animation: fadeIn 0.2s ease;
}

.manual-city-input input {
  flex: 1;
  padding: 10px 14px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.manual-city-input input:focus { border-color: var(--olive); }

.manual-city-input button {
  padding: 10px 20px;
  background: var(--olive);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

/* ─── Settings time pickers ─── */
.time-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 10px;
}

.time-row label {
  font-size: 13px;
  color: var(--ink-lighter);
  min-width: 30px;
}

.time-row input[type="time"] {
  padding: 8px 10px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 14px;
  outline: none;
  color: var(--ink);
}

/* ─── Scrollbar ─── */
.detail-page::-webkit-scrollbar,
.filter-panel::-webkit-scrollbar { width: 0; }

/* ─── Results count ─── */
.results-count {
  padding: 0 20px 8px;
  font-size: 13px;
  color: var(--ink-lighter);
  font-weight: 500;
}

/* ─── Copied toast ─── */
.toast {
  position: fixed;
  bottom: 90px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--ink);
  color: var(--cream);
  padding: 10px 20px;
  border-radius: 100px;
  font-size: 14px;
  font-weight: 500;
  z-index: 200;
  animation: fadeInUp 0.3s ease;
  box-shadow: var(--shadow-lg);
}

/* ─── App version ─── */
.app-version {
  text-align: center;
  font-size: 12px;
  color: var(--ink-lighter);
  padding: 20px;
  opacity: 0.6;
}
`;function wh(){const{markets:o,loading:c,error:u,favorites:f,toggleFav:g,getMarketDetails:x,categories:k,regions:N,cities:F,categoryIcons:X,categoryColors:G,dataMode:q,userLat:te,userLng:_,positionStatus:E,positionError:M,requestPosition:K,clearPosition:Z}=Kp(),[ae,ze]=U.useState("esplora"),[pe,Me]=U.useState("lista"),[he,_e]=U.useState(""),[Ue,He]=U.useState("7giorni"),[qe,nt]=U.useState(!1),H=dh(Ue,he,qe),[B,ne]=U.useState(null),[se,ye]=U.useState(60),[ie,T]=U.useState(!1),[A,$]=U.useState(!1),[v,j]=U.useState("data"),[oe,le]=U.useState(null),[ce,de]=U.useState(!1),[xe,ge]=U.useState(""),[je,Ge]=U.useState(null),[lt,On]=U.useState([]),[$e,Rt]=U.useState(""),[Xe,Ot]=U.useState(""),[jt,Gt]=U.useState(100),[zt,It]=U.useState(!1),[gt,at]=U.useState(0),[or,lr]=U.useState([]),[fn,ar]=U.useState(""),[In,Xt]=U.useState(""),[An,Zt]=U.useState(100),[mt,bn]=U.useState("none"),[Ir,Mi]=U.useState(""),[es,Fi]=U.useState(null);U.useRef(null);const Ar=k.length>0?k:ph,Un=Object.keys(X).length>0?X:mh,$n=Object.keys(G).length>0?G:vh,br=N.length>0?N:hh,Wt=F.length>0?F:gh,Se=Number.isFinite(te)&&Number.isFinite(_),Ur=U.useCallback((h,D)=>{D&&D.stopPropagation(),g(h)},[g]),Jt=U.useCallback(async h=>{le(h),ge(""),de(!0);try{const D=await x(h.id);le(I=>(I==null?void 0:I.id)===h.id?D||h:I)}catch(D){ge(D.message||"Impossibile caricare i dettagli")}finally{de(!1)}},[x]),Nt=U.useCallback(h=>{Ge(h),setTimeout(()=>Ge(null),2e3)},[]);U.useEffect(()=>{const h=()=>{const D=window.location.hash.replace(/^#/,""),I=new URLSearchParams(D).get("mercato"),O=I&&o.find(me=>me.id===I);O&&Jt(O)};return h(),window.addEventListener("hashchange",h),()=>window.removeEventListener("hashchange",h)},[o,Jt]);const Ri=()=>{le(null),window.location.hash.startsWith("#mercato=")&&window.history.replaceState(null,"",window.location.pathname+window.location.search)},Oi=async h=>{var O;const D=new URL(window.location.href);D.hash="mercato="+encodeURIComponent(h.id);const I={title:h.name,text:h.city,url:D.toString()};try{navigator.share?await navigator.share(I):(O=navigator.clipboard)!=null&&O.writeText?(await navigator.clipboard.writeText(I.url),Nt("Link del mercato copiato.")):window.prompt("Copia questo link per condividerlo:",I.url)}catch(me){(me==null?void 0:me.name)!=="AbortError"&&Nt("Condivisione non riuscita.")}},$r=h=>{if(ce||xe){Nt("Indicazioni non disponibili finché i dettagli non sono verificati.");return}const D=Kc(h);if(!D){Nt("Indirizzo non abbastanza preciso per navigare.");return}const I="https://www.google.com/maps/dir/?api=1&destination="+encodeURIComponent(D);window.open(I,"_blank","noopener,noreferrer")},Ii=async h=>{var D,I;if(!((D=h.address)!=null&&D.trim())){Nt("Indirizzo non disponibile.");return}try{if(!((I=navigator.clipboard)!=null&&I.writeText))throw new Error("Clipboard not supported");await navigator.clipboard.writeText(h.address),Nt("Indirizzo copiato.")}catch{Nt("Seleziona il testo dell’indirizzo per copiarlo.")}},pn=()=>{bn("auto"),Se||K()};U.useEffect(()=>{E==="ready"&&Se&&mt==="auto"?(Ot(""),Rt(""),It(!1),Gt(50),at(1+ +(lt.length>0)),j("distanza")):["denied","error","unavailable"].includes(E)&&mt==="auto"&&bn("none")},[E,Se,mt]);const sr=()=>{const h=Ir.trim().toLocaleLowerCase("it"),D=Wt.find(I=>I.toLocaleLowerCase("it")===h);if(!D){Nt("Scegli una città presente nel catalogo.");return}Z(),bn("manual"),Ot(D),Rt(""),Gt(100),j("data"),at(1),ze("esplora"),Nt("Filtra per città: "+D)},Vn=()=>{Z(),bn("none"),Ot(""),Gt(100),at(+(lt.length>0)+ +!!$e),j("data")},ur=o;U.useEffect(()=>ye(60),[he,H,B,lt,$e,Xe,jt,v,Se,zt,B]);const vt=U.useMemo(()=>{let h=[...ur];if(he.trim()){const D=he.toLowerCase();h=h.filter(I=>I.name.toLowerCase().includes(D)||I.city.toLowerCase().includes(D)||I.category.toLowerCase().includes(D)||I.tags.some(O=>O.toLowerCase().includes(D)))}if(H==="oggi")h=h.filter(D=>D.dates.includes(ji));else if(H==="weekend"){const D=Xo.getDay(),I=D===0?-1:6-D,O=new Date(Xo);O.setDate(O.getDate()+I);const me=new Date(O);me.setDate(me.getDate()+1);const Re=dn(O),yt=dn(me);h=h.filter(Ce=>Ce.dates.includes(Re)||Ce.dates.includes(yt))}else if(H==="7giorni"){const D=new Date(Xo);D.setDate(D.getDate()+7);const I=dn(D);h=h.filter(O=>O.dates.some(me=>me>=ji&&me<=I))}if(B!==null&&(h=h.filter(D=>(D.dates||[]).some(I=>I>=ji&&Pi(I)===B))),lt.length>0&&(h=h.filter(D=>lt.includes(D.category))),$e&&(h=h.filter(D=>D.region===$e)),Xe&&(h=h.filter(D=>D.city===Xe)),Se&&jt<100&&(h=h.filter(D=>Number.isFinite(D.distance)&&D.distance<=jt&&(zt||D.positionQuality==="precisa"))),v==="distanza"&&Se){const D=I=>I.positionQuality==="precisa"?0:I.positionQuality==="approssimata"?1:2;h.sort((I,O)=>D(I)-D(O)||(I.distance??1/0)-(O.distance??1/0))}else{const D=I=>(I.dateQuality==="confermata"?50:0)+(I.positionQuality==="precisa"?9:0)+(I.hours?5:0)+(I.category!=="Misto"?3:0);h.sort((I,O)=>{const me=zi(I.dates),Re=zi(O.dates);return(me||"9999").localeCompare(Re||"9999")||D(O)-D(I)||I.name.localeCompare(O.name,"it")})}return h},[ur,he,H,B,lt,$e,Xe,jt,v,Se,zt]),Ct=U.useMemo(()=>qp(vt,{keepSingleWeeklyGroups:B!==null}),[vt,B]),cr=()=>{lr([...lt]),ar($e),Xt(Xe),Zt(jt),T(!0)},Vr=()=>{On(or),Rt(fn),Ot(In),Gt(Se?An:100);let h=0;or.length>0&&h++,fn&&h++,In&&h++,Se&&An<100&&h++,at(h),T(!1)},nl=()=>{lr([]),ar(""),Xt(""),Zt(100),On([]),Rt(""),Ot(""),Gt(100),at(0),It(!1),T(!1)},Ai=()=>{On([]),Rt(""),Ot(""),Gt(100),It(!1),at(0),He(null),nt(!1),ne(null),_e("")};U.useCallback((h,D,I,O)=>{const Et=(D-6.5)/13*I,tn=(47.5-h)/(47.5-36.5)*O;return{x:Et,y:tn}},[]);const bi=(h,D)=>{const I=yh(h.dates,h.dateQuality),O=zi(h.dates),me=$n[h.category]||"#888",Re=f.has(h.id);return a.jsxs("div",{className:"market-card",style:{animationDelay:`${Math.min(D,12)*50}ms`,"--cat-color":me},children:[a.jsx("button",{type:"button",className:"market-card-open","aria-label":"Apri i dettagli di "+h.name+", "+h.city,onClick:()=>Jt(h)}),a.jsx("div",{style:{position:"absolute",left:0,top:0,bottom:0,width:4,background:me,borderRadius:"4px 0 0 4px"}}),a.jsxs("div",{className:"card-top",children:[a.jsxs("div",{className:"card-badges",children:[a.jsxs("span",{className:"category-badge",style:{background:me+"14",color:me},children:[Un[h.category]," ",h.category]}),I&&a.jsx("span",{className:"date-badge",style:{background:I.color},children:I.label})]}),a.jsx("button",{className:`fav-btn ${Re?"active":""}`,onClick:yt=>Ur(h.id,yt),"aria-label":Re?"Rimuovi dai preferiti":"Aggiungi ai preferiti",children:a.jsx(ke,{name:Re?"heartFilled":"heart",size:20})})]}),a.jsx("div",{className:"card-name",children:h.name}),a.jsxs("div",{className:"card-info",children:[a.jsxs("span",{className:"card-info-item",children:[a.jsx(ke,{name:"calendar",size:14,color:"#6C6255"}),Wa(O)]}),a.jsxs("span",{className:"card-info-item",children:[a.jsx(ke,{name:"clock",size:14,color:"#6C6255"}),Ya(h,O)]}),a.jsxs("span",{className:"card-info-item",children:[a.jsx(ke,{name:"mapPin",size:14,color:"#6C6255"}),h.city]}),Se&&a.jsx("span",{className:"card-info-item card-distance",children:h.positionQuality==="precisa"&&Number.isFinite(h.distance)?"a "+Math.round(h.distance)+" km":h.positionQuality==="approssimata"&&Number.isFinite(h.distance)?"circa "+Math.round(h.distance)+" km (stimati)":"Posizione da verificare"})]})]},h.id)},en=()=>a.jsx(U.Suspense,{fallback:a.jsx("div",{role:"status",style:{margin:"22px 18px 110px",padding:22,background:"var(--white)",borderRadius:12,color:"var(--ink-lighter)"},children:"Caricamento mappa interattiva…"}),children:a.jsx(fh,{markets:vt,userLat:te,userLng:_,onSelect:Jt})}),Ui=()=>{var Bn;if(!oe)return null;const h=oe,D=$n[h.category]||"#888",I=f.has(h.id),O=h.dates.filter(R=>R>=ji).sort(),me=!ce&&!xe&&!!Kc(h),Re=sh(h),yt=lh(h),Ce=yt.evidence,Et=uh(h.sourceDetail),tn=Fr(h);return a.jsxs("div",{className:"detail-page",children:[a.jsxs("div",{className:"detail-hero",style:{background:`linear-gradient(135deg, ${D}08 0%, ${D}14 100%)`},children:[a.jsx("div",{style:{position:"absolute",top:-40,right:-40,width:180,height:180,borderRadius:"50%",background:D,opacity:.04}}),a.jsx("button",{className:"detail-back",onClick:Ri,children:a.jsx(ke,{name:"chevronLeft",size:20})}),a.jsxs("div",{className:"detail-actions-top",children:[a.jsx("button",{className:"detail-icon-btn",onClick:()=>Oi(h),"aria-label":"Condividi questo mercato",children:a.jsx(ke,{name:"share",size:18})}),a.jsx("button",{className:`detail-icon-btn ${I?"fav-active":""}`,onClick:()=>Ur(h.id),children:a.jsx(ke,{name:I?"heartFilled":"heart",size:18})})]}),a.jsxs("span",{className:"detail-category-tag",style:{background:D+"18",color:D},children:[Un[h.category]," ",h.category]}),a.jsx("div",{className:"detail-name",children:h.name}),ce&&a.jsx("div",{style:{fontSize:12,marginTop:8},children:"Caricamento dettagli completi…"}),xe&&a.jsxs("div",{role:"alert",style:{fontSize:12,marginTop:8},children:[xe,". Sono visibili i dati sintetici."]}),a.jsxs("div",{className:"detail-city",children:[a.jsx(ke,{name:"mapPin",size:14,color:D,strokeWidth:2})," ",h.city,", ",h.region]})]}),a.jsxs("div",{className:"detail-body",children:[a.jsxs("div",{className:"detail-section",style:{animationDelay:"0.05s"},children:[a.jsxs("div",{className:"detail-section-title",children:[a.jsx(ke,{name:"calendar",size:18,color:D})," Prossime date"]}),a.jsxs("div",{className:"detail-dates-chips",children:[O.length===0&&a.jsx("span",{className:"date-chip",children:"Date da verificare"}),O.map(R=>{const rt=R===ji,st=new Date(R+"T00:00:00").getDay(),rl=st===0||st===6;return a.jsx("span",{className:`date-chip ${rt?"today":rl?"weekend":""}`,title:Ya(h,R),children:Wa(R)},R)})]}),yt.recurrence&&a.jsx("div",{className:"detail-recurrence",children:yt.recurrence}),Ka(h.dates,h.dateQuality)&&a.jsx("div",{style:{fontSize:12,color:"#6C6255",marginTop:8},children:Ka(h.dates,h.dateQuality)})]}),a.jsxs("div",{className:"detail-section",style:{animationDelay:"0.1s"},children:[a.jsxs("div",{className:"detail-section-title",children:[a.jsx(ke,{name:"clock",size:18,color:D})," Orari"]}),a.jsx("div",{className:"detail-hours",style:yt.hours.length>100?{fontSize:15}:void 0,children:yt.hours||(Re.rows.length?"Vedi gli orari delle singole date":"Orari non disponibili")}),Re.notes.map((R,rt)=>a.jsx("p",{className:"source-calendar-note",children:R},R+rt)),Re.rows.length>0&&a.jsxs("details",{className:"source-calendar",open:Re.hasVariations||Re.rows.length<=3,children:[a.jsxs("summary",{children:["Date e orari riportati dalla fonte (",Re.rows.length,")"]}),a.jsx("dl",{children:Re.rows.map(R=>a.jsxs("div",{className:"source-calendar-row","data-period":R.kind==="interval",children:[a.jsx("dt",{children:R.label}),a.jsxs("dd",{children:[R.status&&a.jsxs("strong",{children:[R.status,R.hours?" · ":""]}),R.hours,R.note&&a.jsx("p",{className:"source-calendar-note",children:R.note})]})]},R.key))})]},h.id)]}),Ce&&a.jsxs("div",{className:"detail-section",children:[a.jsxs("div",{className:"detail-section-title",children:[a.jsx(ke,{name:"info",size:18,color:D})," ",Ce.title]}),Ce.notes.map((R,rt)=>a.jsx("p",{className:"source-calendar-note",children:R},R+rt)),Ce.hours&&a.jsxs("p",{className:"detail-description",children:[a.jsxs("strong",{children:[Ce.hoursLabel,":"]})," ",Ce.hours]}),Ce.recurrence&&a.jsxs("p",{className:"source-calendar-note",children:["Cadenza descritta nella pagina: ",Ce.recurrence]}),Ce.rows.length>0&&a.jsxs("details",{className:"source-calendar",open:Ce.rows.length<=3,children:[a.jsxs("summary",{children:["Date e periodi descritti nella pagina (",Ce.rows.length,")"]}),a.jsx("dl",{children:Ce.rows.map(R=>a.jsxs("div",{className:"source-calendar-row","data-period":R.kind==="interval",children:[a.jsx("dt",{children:R.label}),a.jsxs("dd",{children:[a.jsxs("strong",{children:[R.status,R.hours?" · ":""]}),R.hours,R.note&&a.jsx("p",{className:"source-calendar-note",children:R.note})]})]},R.key))})]},h.id+"/editorial"),a.jsxs("p",{className:"source-calendar-note",children:[a.jsx("a",{href:Ce.sourceUrl,target:"_blank",rel:"noopener noreferrer",children:Ce.sourceName})," · pagina letta il "+Ce.readOn,a.jsx("br",{}),Ce.editorialDate]})]}),a.jsxs("div",{className:"detail-section",style:{animationDelay:"0.15s"},children:[a.jsxs("div",{className:"detail-section-title",children:[a.jsx(ke,{name:"mapPin",size:18,color:D})," Indirizzo"]}),tn.length>0&&a.jsx("p",{className:"source-calendar-note",children:"Indirizzo salvato, discordante con la fonte"}),a.jsx("div",{className:"detail-address",children:h.address||"Indirizzo non verificato"}),tn.map(R=>a.jsxs("div",{className:"detail-address-conflict",role:"note",children:[a.jsxs("p",{className:"detail-description",children:["La fonte indica invece: ",a.jsx("strong",{children:R.sourceAddress}),"."]}),a.jsxs("p",{className:"source-calendar-note",children:[a.jsx("a",{href:R.sourceUrl,target:"_blank",rel:"noopener noreferrer",children:"Happings"})," · pagina letta il "+R.readOnLabel]})]},R.key)),h.locationReviewRequired&&a.jsxs("p",{role:"note",style:{color:"#857660",fontSize:12,lineHeight:1.5,margin:"9px 0"},children:[mp," Le indicazioni stradali per questa scheda sono disabilitate."]}),h.positionQuality!=="precisa"&&a.jsx("div",{style:{fontSize:12,color:"#6C6255",marginTop:6},children:"Posizione indicativa o da verificare"}),!me&&!ce&&a.jsx("div",{role:"note",style:{fontSize:12,color:"#6C6255",margin:"10px 0"},children:tn.length>0?"Indicazioni sospese: l’indirizzo salvato è discordante con la fonte.":"Indicazioni non disponibili: manca una sede riconciliata e verificabile."}),a.jsxs("div",{className:"detail-address-actions",children:[a.jsxs("button",{className:"btn-primary",onClick:()=>$r(h),disabled:!me,title:me?"Apri indicazioni stradali":"Dettagli o sede non sufficienti per navigare",children:[a.jsx(ke,{name:"navigation",size:16,color:"white"})," Indicazioni"]}),a.jsxs("button",{className:"btn-secondary",onClick:()=>Ii(h),disabled:!((Bn=h.address)!=null&&Bn.trim()),title:tn.length>0?"Copia l’indirizzo salvato, segnalato come discordante":"Copia indirizzo",children:[a.jsx(ke,{name:"copy",size:16})," Copia"]})]})]}),h.description&&a.jsxs("div",{className:"detail-section",style:{animationDelay:"0.2s"},children:[a.jsxs("div",{className:"detail-section-title",children:[a.jsx(ke,{name:"info",size:18,color:D})," Descrizione"]}),a.jsx("div",{className:"detail-description",children:h.description})]}),(Et.organizer||Et.links.length>0)&&a.jsxs("div",{className:"detail-section",children:[a.jsxs("div",{className:"detail-section-title",children:[a.jsx(ke,{name:"info",size:18,color:D})," Contatti riportati dalla fonte"]}),Et.organizer&&a.jsxs("p",{className:"detail-description",children:["Organizzatore:"," ",Et.organizer.href?a.jsx("a",{href:Et.organizer.href,target:"_blank",rel:"noopener noreferrer",children:Et.organizer.label}):Et.organizer.label]}),Et.links.map((R,rt)=>a.jsx("p",{className:"detail-description",style:{marginTop:6,overflowWrap:"anywhere"},children:a.jsx("a",{href:R.href,target:"_blank",rel:"noopener noreferrer",children:R.label})},R.href+rt))]}),h.tags&&h.tags.length>0&&a.jsxs("div",{className:"detail-section",style:{animationDelay:"0.25s"},children:[a.jsx("div",{className:"detail-section-title",children:"Tag"}),a.jsx("div",{className:"detail-tags",children:h.tags.map(R=>a.jsx("span",{className:"detail-tag",children:R},R))})]}),a.jsx("div",{className:"detail-section",style:{animationDelay:"0.3s"},children:a.jsxs("div",{className:"detail-provenance",children:[a.jsxs("div",{style:{flex:1},children:[a.jsx("div",{style:{fontSize:13,marginBottom:2},children:h.lastVerified?"Verificato il "+h.lastVerified:"Verifica individuale non documentata"}),a.jsxs("div",{style:{fontSize:12,opacity:.7},children:["Fonte: ",h.source||"non disponibile",h.sourceUpdated?h.sourceUpdateScope==="dataset"?" · dataset aggiornato il "+h.sourceUpdated+" (non verifica del singolo mercato)":" · data dichiarata dalla fonte: "+h.sourceUpdated:""]}),h.sourceUrl&&a.jsx("a",{href:h.sourceUrl,target:"_blank",rel:"noopener noreferrer",style:{display:"inline-block",fontSize:12,marginTop:5},children:"Controlla la fonte originale"}),(h.sourceEvidence||[]).filter(R=>R.url!==h.sourceUrl).slice(0,3).map((R,rt)=>a.jsxs("div",{style:{fontSize:12,marginTop:5,lineHeight:1.4},children:["Fonte aggiuntiva:"," ",a.jsx("a",{href:R.url,target:"_blank",rel:"noopener noreferrer",children:R.nome})]},R.url+rt)),(h.fieldEvidence||[]).map((R,rt)=>a.jsxs("div",{style:{fontSize:12,marginTop:10,lineHeight:1.5},children:[a.jsxs("strong",{children:[R.fields,": riscontro nella fonte"]}),a.jsx("br",{}),a.jsx("a",{href:R.sourceUrl,target:"_blank",rel:"noopener noreferrer",children:R.sourceName})," · letta il "+R.readOn,a.jsx("br",{}),R.sourceDate?"Data dei contenuti: "+R.sourceDate:"Data dei contenuti non dichiarata"]},R.sourceUrl+R.readOn+rt)),(h.calendarExceptions||[]).filter(R=>R.data>=new Date().toISOString().slice(0,10)).map((R,rt)=>a.jsxs("div",{style:{fontSize:12,marginTop:10,lineHeight:1.5},children:[a.jsxs("strong",{children:[R.data,": edizione annullata"]}),a.jsx("br",{}),R.motivo," ",a.jsx("a",{href:R.url,target:"_blank",rel:"noopener noreferrer",children:"Fonte"})]},R.data+rt))]}),a.jsxs("div",{style:{textAlign:"right"},children:[a.jsx("div",{style:{fontSize:11,marginBottom:4},children:"Completezza dati"}),a.jsx("div",{className:"confidence-bar",children:a.jsx("div",{className:"confidence-fill",style:{width:`${h.dataCompleteness}%`,background:h.dataCompleteness>80?"#446E47":h.dataCompleteness>55?"#805B08":"#B94439"}})}),a.jsx("div",{style:{fontSize:10,maxWidth:135,marginTop:5},children:"Campi compilati, non verifica delle informazioni"})]})]})}),a.jsx("div",{style:{height:40}})]})]})},$i=()=>a.jsxs(a.Fragment,{children:[a.jsx("div",{className:"filter-overlay",onClick:()=>T(!1)}),a.jsxs("div",{className:"filter-panel",children:[a.jsxs("div",{className:"filter-header",children:[a.jsx("span",{className:"filter-title",children:"Filtri"}),a.jsx("button",{className:"filter-close",onClick:()=>T(!1),children:a.jsx(ke,{name:"x",size:18})})]}),a.jsxs("div",{className:"filter-body",children:[a.jsxs("div",{className:"filter-section",children:[a.jsx("div",{className:"filter-section-label",children:"Categoria"}),a.jsx("div",{className:"filter-categories",children:Ar.map(h=>{const D=or.includes(h),I=$n[h];return a.jsxs("button",{className:`filter-cat-chip ${D?"active":""}`,style:D?{borderColor:I,color:I,background:I+"10"}:{},onClick:()=>{lr(O=>O.includes(h)?O.filter(me=>me!==h):[...O,h])},children:[Un[h]," ",h]},h)})})]}),a.jsxs("div",{className:"filter-section",children:[a.jsx("div",{className:"filter-section-label",children:"Regione"}),a.jsxs("select",{className:"filter-select",value:fn,onChange:h=>{ar(h.target.value),Xt("")},children:[a.jsx("option",{value:"",children:"Tutte le regioni"}),br.map(h=>a.jsx("option",{value:h,children:h},h))]})]}),a.jsxs("div",{className:"filter-section",children:[a.jsx("div",{className:"filter-section-label",children:"Città"}),a.jsxs("select",{className:"filter-select",value:In,onChange:h=>Xt(h.target.value),children:[a.jsx("option",{value:"",children:"Tutte le città"}),Wt.filter(h=>{var D;return!fn||((D=o.find(I=>I.city===h))==null?void 0:D.region)===fn}).map(h=>a.jsx("option",{value:h,children:h},h))]})]}),a.jsxs("div",{className:"filter-section",children:[a.jsx("div",{className:"filter-section-label",children:"Distanza massima"}),a.jsxs("div",{className:"range-container",children:[a.jsxs("div",{className:"range-label",children:[a.jsx("span",{children:"0 km"}),a.jsxs("span",{className:"range-value",children:[An," km"]})]}),a.jsx("input",{type:"range",className:"range-input",min:5,max:100,step:5,value:An,disabled:!Se,onChange:h=>Zt(Number(h.target.value))}),!Se&&a.jsx("div",{className:"setting-sublabel",children:"Per usare il raggio, attiva la posizione in Impostazioni."})]})]})]}),a.jsxs("div",{className:"filter-footer",children:[a.jsx("button",{className:"filter-reset",onClick:nl,children:"Reimposta filtri"}),a.jsx("button",{className:"filter-apply",onClick:Vr,children:"Applica filtri"})]})]})]}),Vi=()=>a.jsxs(a.Fragment,{children:[a.jsxs("div",{className:"header",children:[a.jsxs("div",{className:"header-title",children:[a.jsx("span",{className:"accent",children:"Mercati"})," d'Italia"]}),a.jsxs("div",{className:"search-container",children:[a.jsx("span",{className:"search-icon",children:a.jsx(ke,{name:"search",size:18})}),a.jsx("input",{className:"search-input",placeholder:"Cerca città, mercato o parola chiave",value:he,onChange:h=>_e(h.target.value)})]}),a.jsx("div",{className:"chips-row",children:[{key:"oggi",label:"Oggi"},{key:"weekend",label:"Questo weekend"},{key:"7giorni",label:"Prossimi 7 giorni"}].map(({key:h,label:D})=>a.jsx("button",{className:`chip ${H===h?"active":""}`,onClick:()=>{He(H===h?null:h),nt(!0)},children:D},h))}),pe==="lista"&&a.jsxs("div",{className:"chips-row","aria-label":"Filtra per giorno della settimana",style:{gap:5,marginTop:3,paddingBottom:5,flexWrap:"nowrap",overflowX:"auto",scrollbarWidth:"thin"},children:[id.map((h,D)=>a.jsx("button",{type:"button","aria-pressed":B===D,"aria-label":"Mostra mercati del "+["lunedì","martedì","mercoledì","giovedì","venerdì","sabato","domenica"][D],className:`chip ${B===D?"active":""}`,style:{flexShrink:0,minWidth:39,padding:"7px 10px",fontSize:12},onClick:()=>{ne(I=>I===D?null:D),B!==D&&He("7giorni")},children:h},h)),B!==null&&a.jsx("button",{type:"button",className:"chip",style:{flexShrink:0,padding:"7px 9px"},onClick:()=>ne(null),"aria-label":"Togli filtro giorno",children:"×"})]}),pe==="lista"&&!Se&&!Xe&&!$e&&!he.trim()&&a.jsxs("div",{role:"note",style:{background:"#F0EEE8",borderRadius:12,padding:"12px 14px",margin:"6px 0 12px",fontSize:12,lineHeight:1.5,color:"var(--ink-light)"},children:[a.jsx("strong",{style:{display:"block",marginBottom:3,fontSize:13,color:"var(--ink)"},children:"Stai esplorando tutta Italia"}),"Cerca la tua città nella barra sopra, oppure usa la posizione per trovare mercati nella tua zona. Le date automatiche non sono conferme degli organizzatori.",a.jsx("div",{style:{display:"flex",gap:6,marginTop:9,flexWrap:"wrap"},children:["Firenze","Roma","Milano"].map(h=>a.jsx("button",{type:"button",className:"chip",onClick:()=>{Rt(""),Ot(h),at(1),Me("lista")},children:h},h))})]}),(Xe||$e||lt.length>0)&&a.jsxs("div",{className:"chips-row",style:{gap:8,alignItems:"center",margin:"2px 0 8px"},children:[Xe&&a.jsxs("button",{className:"chip active",onClick:()=>{Ot(""),at(Math.max(0,gt-1))},"aria-label":"Rimuovi filtro città "+Xe,children:["Città: ",Xe," ×"]}),$e&&a.jsxs("button",{className:"chip active",onClick:()=>{Rt(""),at(Math.max(0,gt-1))},"aria-label":"Rimuovi filtro regione "+$e,children:["Regione: ",$e," ×"]}),lt.length>0&&a.jsx("button",{className:"chip active",onClick:()=>{On([]),at(Math.max(0,gt-1))},children:"Categorie ×"}),a.jsx("button",{className:"chip",onClick:Ai,children:"Azzera filtri"})]}),a.jsxs("div",{className:"chips-row",style:{marginTop:8,alignItems:"center"},children:[a.jsxs("button",{className:`chip ${Se?"active":""}`,onClick:pn,disabled:E==="requesting",children:[a.jsx(ke,{name:"mapPin",size:13}),E==="ready"?zt?"Vicino a me · posizioni indicative":"Vicino a me · 50 km, posizioni precise":E==="requesting"?"Cerco la posizione…":"Mercati vicino a me"]}),M&&a.jsx("span",{role:"alert",style:{fontSize:12,color:"#A5443D"},children:M})]}),Se&&jt<100&&a.jsxs("div",{role:"note",style:{fontSize:12,lineHeight:1.5,color:"#7D7267",margin:"4px 20px 10px"},children:[zt?"Mostriamo anche mercati con coordinate non verificate. Alcuni possono non essere davvero vicini.":"Nel raggio mostriamo solo mercati con posizione precisa. Altri mercati possono mancare.",a.jsx("button",{className:"chip",style:{display:"block",marginTop:8},onClick:()=>It(h=>!h),children:zt?"Escludi posizioni indicative":"Mostra anche posizioni indicative"})]}),a.jsxs("div",{className:"controls-row",children:[a.jsxs("div",{className:"view-toggle",children:[a.jsxs("button",{className:pe==="lista"?"active":"",onClick:()=>Me("lista"),children:[a.jsx(ke,{name:"list",size:14})," Lista"]}),a.jsxs("button",{className:pe==="mappa"?"active":"",onClick:()=>Me("mappa"),children:[a.jsx(ke,{name:"map",size:14})," Mappa"]})]}),a.jsxs("div",{style:{position:"relative"},children:[a.jsxs("button",{className:"sort-btn",onClick:()=>$(!A),children:[a.jsx(ke,{name:"sort",size:14})," Ordina"]}),A&&a.jsx("div",{className:"sort-dropdown",children:[{key:"data",label:"Data",icon:"calendar"},{key:"distanza",label:"Distanza",icon:"mapPin"}].map(({key:h,label:D,icon:I})=>a.jsxs("button",{className:`sort-option ${v===h?"active":""}`,disabled:h==="distanza"&&!Se,title:h==="distanza"&&!Se?"Attiva la posizione per ordinare per distanza":"",onClick:()=>{j(h),$(!1)},children:[a.jsx(ke,{name:I,size:16})," ",D,v===h&&a.jsx(ke,{name:"check",size:16,color:"#B94439"})]},h))})]}),a.jsxs("button",{className:`filter-btn ${gt>0?"has-filters":""}`,onClick:cr,children:[a.jsx(ke,{name:"filter",size:14})," Filtri",gt>0&&a.jsx("span",{className:"filter-count",children:gt})]})]})]}),a.jsxs("div",{className:"results-count",style:{display:"flex",alignItems:"center",justifyContent:"space-between"},children:[a.jsxs("span",{children:[c?"Caricamento mercati statici...":`${vt.length.toLocaleString("it-IT")} ${H?"appuntament"+(vt.length===1?"o":"i")+" "+(H==="oggi"?"previsti oggi":H==="weekend"?"previsti nel weekend":"previsti nei prossimi 7 giorni"):"sched"+(vt.length===1?"a":"e")+" nel catalogo"}${Xe?" · "+Xe:$e?" · "+$e:Se?"":" · Italia"}`,pe==="lista"&&Ct.length<vt.length&&!c&&` · ${Ct.length.toLocaleString("it-IT")} schede`]}),q==="demo"&&a.jsx("span",{style:{fontSize:10,fontWeight:700,letterSpacing:"0.05em",padding:"2px 8px",borderRadius:100,background:"var(--sand)",color:"var(--ink-lighter)"},children:"DEMO"})]}),u&&!c&&a.jsxs("div",{role:"alert",className:"empty-state",children:[a.jsx("div",{className:"empty-title",children:"Catalogo temporaneamente non disponibile"}),a.jsx("div",{className:"empty-text",children:u})]}),c?a.jsx("div",{className:"markets-list",children:[1,2,3].map(h=>a.jsx("div",{className:"market-card",style:{height:120,animation:"none",background:"linear-gradient(90deg, var(--white) 25%, var(--beige) 50%, var(--white) 75%)",backgroundSize:"200% 100%",animationName:"shimmer",animationDuration:"1.5s",animationIterationCount:"infinite",animationTimingFunction:"linear"}},h))}):pe==="lista"?a.jsx("div",{className:"markets-list",children:Ct.length>0?a.jsxs(a.Fragment,{children:[Ct.slice(0,se).map((h,D)=>h.kind==="group"?a.jsx(ch,{group:h,loadMarket:x,onOpenMarket:Jt,selectedWeekday:B,autoExpand:Gp(h,B,Xe,he)},h.key):bi(h.market,D)),se<Ct.length&&a.jsxs("button",{className:"btn-secondary",onClick:()=>ye(h=>h+60),style:{margin:"18px auto 30px",padding:"12px 24px",display:"block"},children:["Mostra altre schede (",Math.min(se,Ct.length)," di ",Ct.length,")"]})]}):a.jsxs("div",{className:"empty-state",children:[a.jsx("div",{className:"empty-icon",children:"🔍"}),a.jsx("div",{className:"empty-title",children:"Nessun mercato trovato"}),a.jsx("div",{className:"empty-text",children:Se&&jt<100&&!zt?"Nessun mercato con posizione precisa in questo raggio e periodo. Puoi includere quelli con posizione indicativa.":"Prova a cambiare data, distanza, città o categoria."}),Se&&jt<100&&!zt&&a.jsx("button",{className:"btn-secondary",style:{padding:"10px 18px",marginTop:12},onClick:()=>It(!0),children:"Mostra posizioni indicative"}),a.jsx("button",{style:{marginTop:16,padding:"10px 24px",background:"var(--terracotta)",color:"white",border:"none",borderRadius:100,fontFamily:"var(--font-body)",fontSize:14,fontWeight:600,cursor:"pointer"},onClick:Ai,children:"Reimposta"})]})}):en()]}),Bi=()=>{const h=ur.filter(D=>f.has(D.id));return a.jsxs(a.Fragment,{children:[a.jsx("div",{className:"header",children:a.jsx("div",{className:"header-title",children:"Preferiti"})}),a.jsx("div",{className:"page-content",children:h.length>0?a.jsx("div",{className:"markets-list",style:{padding:0},children:h.map((D,I)=>bi(D,I))}):a.jsxs("div",{className:"empty-state",children:[a.jsx("div",{className:"empty-icon",children:"❤️"}),a.jsx("div",{className:"empty-title",children:"Nessun preferito"}),a.jsx("div",{className:"empty-text",children:"Salva i mercati che ti interessano per ritrovarli qui."})]})})]})},Wi=()=>{const h=ur.filter(O=>f.has(O.id)),D=h.map(O=>({market:O,next:zi(O.dates)})).filter(O=>O.next).sort((O,me)=>O.next.localeCompare(me.next)).slice(0,30),I=h.filter(O=>!zi(O.dates));return a.jsxs(a.Fragment,{children:[a.jsx("div",{className:"header",children:a.jsx("div",{className:"header-title",children:"Agenda preferiti"})}),a.jsxs("div",{className:"page-content",children:[a.jsxs("div",{className:"setting-card",children:[a.jsx("div",{className:"setting-label",children:"I prossimi mercati che hai salvato"}),a.jsx("div",{className:"setting-sublabel",children:"Qui trovi le date disponibili. Le notifiche push automatiche non sono ancora attive. Controlla sempre se la data è confermata prima di partire."})]}),h.length===0?a.jsxs("div",{className:"empty-state",children:[a.jsx("div",{className:"empty-icon",children:"♡"}),a.jsx("div",{className:"empty-title",children:"Nessun mercato salvato"}),a.jsx("div",{className:"empty-text",children:"Salva un mercato dalla ricerca per vederlo qui."}),a.jsx("button",{className:"btn-primary",style:{padding:"10px 20px",marginTop:12},onClick:()=>ze("esplora"),children:"Cerca mercati"})]}):a.jsxs(a.Fragment,{children:[D.length>0?a.jsx("div",{className:"markets-list",style:{padding:0},children:D.map(({market:O,next:me},Re)=>a.jsxs("button",{className:"setting-card",style:{display:"flex",width:"100%",textAlign:"left",gap:12,alignItems:"center",cursor:"pointer",border:"none"},onClick:()=>Jt(O),children:[a.jsx("span",{style:{minWidth:85,fontWeight:700},children:Wa(me)}),a.jsxs("span",{style:{flex:1},children:[a.jsx("strong",{children:O.name}),a.jsxs("span",{style:{display:"block",fontSize:12,opacity:.75},children:[O.city," · ",O.dateQuality==="confermata"?"Confermata":O.dateQuality==="riportata"?"Riportata dalla fonte":"Prevista, da verificare"]})]})]},O.id))}):a.jsx("div",{className:"setting-card",children:"Nessuna data futura disponibile per i tuoi preferiti."}),I.length>0&&a.jsxs("div",{className:"setting-card",style:{marginTop:12},children:[a.jsxs("div",{className:"setting-label",children:[I.length," preferiti senza prossima data"]}),a.jsx("div",{className:"setting-sublabel",children:"Li trovi nella sezione Preferiti. Verifica la fonte ufficiale."})]})]})]})]})},Hi=()=>a.jsxs(a.Fragment,{children:[a.jsx("div",{className:"header",children:a.jsx("div",{className:"header-title",children:"Impostazioni"})}),a.jsxs("div",{className:"page-content",children:[a.jsxs("div",{className:"setting-card",children:[a.jsx("div",{className:"setting-label",style:{marginBottom:4},children:"Posizione"}),a.jsx("div",{className:"setting-sublabel",children:"Scegli come trovare i mercati vicino a te"}),a.jsxs("div",{className:"location-options",children:[a.jsxs("button",{className:`location-option ${mt==="auto"?"active":""}`,onClick:pn,children:[a.jsx("div",{className:"icon-circle",children:a.jsx(ke,{name:"compass",size:18})}),a.jsxs("div",{children:[a.jsx("div",{style:{fontWeight:600},children:"Usa la mia posizione"}),a.jsx("div",{style:{fontSize:12,color:"#6C6255",marginTop:1},children:E==="ready"?"Posizione attiva":E==="requesting"?"Richiesta in corso…":"Richiede il tuo consenso"})]})]}),a.jsxs("button",{className:`location-option ${mt==="manual"?"active":""}`,onClick:()=>bn("manual"),children:[a.jsx("div",{className:"icon-circle",children:a.jsx(ke,{name:"mapPin",size:18})}),a.jsxs("div",{children:[a.jsx("div",{style:{fontWeight:600},children:"Scegli una città"}),a.jsx("div",{style:{fontSize:12,color:"#6C6255",marginTop:1},children:"Inserisci manualmente"})]})]}),a.jsxs("button",{className:`location-option ${mt==="none"?"active":""}`,onClick:Vn,children:[a.jsx("div",{className:"icon-circle",children:a.jsx(ke,{name:"x",size:18})}),a.jsxs("div",{children:[a.jsx("div",{style:{fontWeight:600},children:"Non ora"}),a.jsx("div",{style:{fontSize:12,color:"#6C6255",marginTop:1},children:"Naviga senza posizione"})]})]})]}),M&&a.jsx("div",{role:"alert",className:"setting-sublabel",style:{marginTop:12},children:M}),Se&&a.jsx("div",{className:"setting-sublabel",style:{marginTop:10},children:"Distanze calcolate rispetto alla tua posizione. Alcuni mercati hanno solo coordinate indicative."}),mt==="manual"&&a.jsxs(a.Fragment,{children:[a.jsxs("div",{className:"manual-city-input",children:[a.jsx("input",{list:"available-market-cities",placeholder:"Es. Firenze",value:Ir,onChange:h=>Mi(h.target.value),onKeyDown:h=>{h.key==="Enter"&&sr()}}),a.jsx("datalist",{id:"available-market-cities",children:Wt.map(h=>a.jsx("option",{value:h},h))}),a.jsx("button",{onClick:sr,children:"Filtra città"})]}),a.jsx("div",{className:"setting-sublabel",children:"La città selezionata filtra i risultati. Non equivale alla posizione GPS."})]})]}),a.jsxs("div",{className:"app-version",children:[a.jsxs("div",{style:{fontFamily:"var(--font-display)",fontSize:16,marginBottom:4},children:[a.jsx("span",{style:{color:"var(--terracotta)"},children:"Mercati"})," d'Italia"]}),"Versione 1.1 · Catalogo statico (lettura gratuita)"]})]})]});return a.jsxs(a.Fragment,{children:[a.jsx("style",{children:xh}),a.jsxs("div",{className:"app-container",onClick:()=>A&&$(!1),children:[ae==="esplora"&&Vi(),ae==="mappa"&&Vi(),ae==="preferiti"&&Bi(),ae==="notifiche"&&Wi(),ae==="impostazioni"&&Hi(),ie&&$i(),oe&&Ui(),je&&a.jsx("div",{className:"toast",children:je}),a.jsx("nav",{className:"bottom-tabs",children:[{id:"esplora",label:"Esplora",icon:"compass"},{id:"preferiti",label:"Preferiti",icon:"heart"},{id:"notifiche",label:"Agenda",icon:"calendar"},{id:"impostazioni",label:"Impostazioni",icon:"settings"}].map(h=>a.jsxs("button",{className:`tab-btn ${ae===h.id?"active":""}`,onClick:()=>{ze(h.id),h.id==="esplora"&&Me("lista")},children:[a.jsx(ke,{name:h.icon,size:22,strokeWidth:ae===h.id?2:1.6}),h.label]},h.id))})]})]})}up.createRoot(document.getElementById("root")).render(a.jsx(np.StrictMode,{children:a.jsx(wh,{})}));export{a as j,U as r};
