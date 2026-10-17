const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["./MarketsMap-B15qIIIi.js","./MarketsMap-MG_XUJyD.css"])))=>i.map(i=>d[i]);
(function(){const h=document.createElement("link").relList;if(h&&h.supports&&h.supports("modulepreload"))return;for(const x of document.querySelectorAll('link[rel="modulepreload"]'))w(x);new MutationObserver(x=>{for(const E of x)if(E.type==="childList")for(const L of E.addedNodes)L.tagName==="LINK"&&L.rel==="modulepreload"&&w(L)}).observe(document,{childList:!0,subtree:!0});function f(x){const E={};return x.integrity&&(E.integrity=x.integrity),x.referrerPolicy&&(E.referrerPolicy=x.referrerPolicy),x.crossOrigin==="use-credentials"?E.credentials="include":x.crossOrigin==="anonymous"?E.credentials="omit":E.credentials="same-origin",E}function w(x){if(x.ep)return;x.ep=!0;const E=f(x);fetch(x.href,E)}})();function dc(s){return s&&s.__esModule&&Object.prototype.hasOwnProperty.call(s,"default")?s.default:s}var ya={exports:{}},si={},xa={exports:{}},re={};/**
 * @license React
 * react.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var ec;function rf(){if(ec)return re;ec=1;var s=Symbol.for("react.element"),h=Symbol.for("react.portal"),f=Symbol.for("react.fragment"),w=Symbol.for("react.strict_mode"),x=Symbol.for("react.profiler"),E=Symbol.for("react.provider"),L=Symbol.for("react.context"),O=Symbol.for("react.forward_ref"),U=Symbol.for("react.suspense"),le=Symbol.for("react.memo"),X=Symbol.for("react.lazy"),K=Symbol.iterator;function ee(m){return m===null||typeof m!="object"?null:(m=K&&m[K]||m["@@iterator"],typeof m=="function"?m:null)}var ve={isMounted:function(){return!1},enqueueForceUpdate:function(){},enqueueReplaceState:function(){},enqueueSetState:function(){}},ne=Object.assign,te={};function H(m,k,q){this.props=m,this.context=k,this.refs=te,this.updater=q||ve}H.prototype.isReactComponent={},H.prototype.setState=function(m,k){if(typeof m!="object"&&typeof m!="function"&&m!=null)throw Error("setState(...): takes an object of state variables to update or a function which returns an object of state variables.");this.updater.enqueueSetState(this,m,k,"setState")},H.prototype.forceUpdate=function(m){this.updater.enqueueForceUpdate(this,m,"forceUpdate")};function Fe(){}Fe.prototype=H.prototype;function we(m,k,q){this.props=m,this.context=k,this.refs=te,this.updater=q||ve}var Ne=we.prototype=new Fe;Ne.constructor=we,ne(Ne,H.prototype),Ne.isPureReactComponent=!0;var de=Array.isArray,Me=Object.prototype.hasOwnProperty,fe={current:null},ke={key:!0,ref:!0,__self:!0,__source:!0};function Ue(m,k,q){var J,ie={},oe=null,he=null;if(k!=null)for(J in k.ref!==void 0&&(he=k.ref),k.key!==void 0&&(oe=""+k.key),k)Me.call(k,J)&&!ke.hasOwnProperty(J)&&(ie[J]=k[J]);var pe=arguments.length-2;if(pe===1)ie.children=q;else if(1<pe){for(var Se=Array(pe),Ge=0;Ge<pe;Ge++)Se[Ge]=arguments[Ge+2];ie.children=Se}if(m&&m.defaultProps)for(J in pe=m.defaultProps,pe)ie[J]===void 0&&(ie[J]=pe[J]);return{$$typeof:s,type:m,key:oe,ref:he,props:ie,_owner:fe.current}}function Ke(m,k){return{$$typeof:s,type:m.type,key:k,ref:m.ref,props:m.props,_owner:m._owner}}function Ye(m){return typeof m=="object"&&m!==null&&m.$$typeof===s}function $(m){var k={"=":"=0",":":"=2"};return"$"+m.replace(/[=:]/g,function(q){return k[q]})}var ye=/\/+/g;function D(m,k){return typeof m=="object"&&m!==null&&m.key!=null?$(""+m.key):k.toString(36)}function Z(m,k,q,J,ie){var oe=typeof m;(oe==="undefined"||oe==="boolean")&&(m=null);var he=!1;if(m===null)he=!0;else switch(oe){case"string":case"number":he=!0;break;case"object":switch(m.$$typeof){case s:case h:he=!0}}if(he)return he=m,ie=ie(he),m=J===""?"."+D(he,0):J,de(ie)?(q="",m!=null&&(q=m.replace(ye,"$&/")+"/"),Z(ie,k,q,"",function(Ge){return Ge})):ie!=null&&(Ye(ie)&&(ie=Ke(ie,q+(!ie.key||he&&he.key===ie.key?"":(""+ie.key).replace(ye,"$&/")+"/")+m)),k.push(ie)),1;if(he=0,J=J===""?".":J+":",de(m))for(var pe=0;pe<m.length;pe++){oe=m[pe];var Se=J+D(oe,pe);he+=Z(oe,k,q,Se,ie)}else if(Se=ee(m),typeof Se=="function")for(m=Se.call(m),pe=0;!(oe=m.next()).done;)oe=oe.value,Se=J+D(oe,pe++),he+=Z(oe,k,q,Se,ie);else if(oe==="object")throw k=String(m),Error("Objects are not valid as a React child (found: "+(k==="[object Object]"?"object with keys {"+Object.keys(m).join(", ")+"}":k)+"). If you meant to render a collection of children, use an array instead.");return he}function ae(m,k,q){if(m==null)return m;var J=[],ie=0;return Z(m,J,"","",function(oe){return k.call(q,oe,ie++)}),J}function se(m){if(m._status===-1){var k=m._result;k=k(),k.then(function(q){(m._status===0||m._status===-1)&&(m._status=1,m._result=q)},function(q){(m._status===0||m._status===-1)&&(m._status=2,m._result=q)}),m._status===-1&&(m._status=0,m._result=k)}if(m._status===1)return m._result.default;throw m._result}var G={current:null},P={transition:null},B={ReactCurrentDispatcher:G,ReactCurrentBatchConfig:P,ReactCurrentOwner:fe};function F(){throw Error("act(...) is not supported in production builds of React.")}return re.Children={map:ae,forEach:function(m,k,q){ae(m,function(){k.apply(this,arguments)},q)},count:function(m){var k=0;return ae(m,function(){k++}),k},toArray:function(m){return ae(m,function(k){return k})||[]},only:function(m){if(!Ye(m))throw Error("React.Children.only expected to receive a single React element child.");return m}},re.Component=H,re.Fragment=f,re.Profiler=x,re.PureComponent=we,re.StrictMode=w,re.Suspense=U,re.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED=B,re.act=F,re.cloneElement=function(m,k,q){if(m==null)throw Error("React.cloneElement(...): The argument must be a React element, but you passed "+m+".");var J=ne({},m.props),ie=m.key,oe=m.ref,he=m._owner;if(k!=null){if(k.ref!==void 0&&(oe=k.ref,he=fe.current),k.key!==void 0&&(ie=""+k.key),m.type&&m.type.defaultProps)var pe=m.type.defaultProps;for(Se in k)Me.call(k,Se)&&!ke.hasOwnProperty(Se)&&(J[Se]=k[Se]===void 0&&pe!==void 0?pe[Se]:k[Se])}var Se=arguments.length-2;if(Se===1)J.children=q;else if(1<Se){pe=Array(Se);for(var Ge=0;Ge<Se;Ge++)pe[Ge]=arguments[Ge+2];J.children=pe}return{$$typeof:s,type:m.type,key:ie,ref:oe,props:J,_owner:he}},re.createContext=function(m){return m={$$typeof:L,_currentValue:m,_currentValue2:m,_threadCount:0,Provider:null,Consumer:null,_defaultValue:null,_globalName:null},m.Provider={$$typeof:E,_context:m},m.Consumer=m},re.createElement=Ue,re.createFactory=function(m){var k=Ue.bind(null,m);return k.type=m,k},re.createRef=function(){return{current:null}},re.forwardRef=function(m){return{$$typeof:O,render:m}},re.isValidElement=Ye,re.lazy=function(m){return{$$typeof:X,_payload:{_status:-1,_result:m},_init:se}},re.memo=function(m,k){return{$$typeof:le,type:m,compare:k===void 0?null:k}},re.startTransition=function(m){var k=P.transition;P.transition={};try{m()}finally{P.transition=k}},re.unstable_act=F,re.useCallback=function(m,k){return G.current.useCallback(m,k)},re.useContext=function(m){return G.current.useContext(m)},re.useDebugValue=function(){},re.useDeferredValue=function(m){return G.current.useDeferredValue(m)},re.useEffect=function(m,k){return G.current.useEffect(m,k)},re.useId=function(){return G.current.useId()},re.useImperativeHandle=function(m,k,q){return G.current.useImperativeHandle(m,k,q)},re.useInsertionEffect=function(m,k){return G.current.useInsertionEffect(m,k)},re.useLayoutEffect=function(m,k){return G.current.useLayoutEffect(m,k)},re.useMemo=function(m,k){return G.current.useMemo(m,k)},re.useReducer=function(m,k,q){return G.current.useReducer(m,k,q)},re.useRef=function(m){return G.current.useRef(m)},re.useState=function(m){return G.current.useState(m)},re.useSyncExternalStore=function(m,k,q){return G.current.useSyncExternalStore(m,k,q)},re.useTransition=function(){return G.current.useTransition()},re.version="18.3.1",re}var tc;function _a(){return tc||(tc=1,xa.exports=rf()),xa.exports}/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var nc;function lf(){if(nc)return si;nc=1;var s=_a(),h=Symbol.for("react.element"),f=Symbol.for("react.fragment"),w=Object.prototype.hasOwnProperty,x=s.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner,E={key:!0,ref:!0,__self:!0,__source:!0};function L(O,U,le){var X,K={},ee=null,ve=null;le!==void 0&&(ee=""+le),U.key!==void 0&&(ee=""+U.key),U.ref!==void 0&&(ve=U.ref);for(X in U)w.call(U,X)&&!E.hasOwnProperty(X)&&(K[X]=U[X]);if(O&&O.defaultProps)for(X in U=O.defaultProps,U)K[X]===void 0&&(K[X]=U[X]);return{$$typeof:h,type:O,key:ee,ref:ve,props:K,_owner:x.current}}return si.Fragment=f,si.jsx=L,si.jsxs=L,si}var rc;function of(){return rc||(rc=1,ya.exports=lf()),ya.exports}var o=of(),T=_a();const af=dc(T);var Ll={},wa={exports:{}},dt={},ka={exports:{}},Sa={};/**
 * @license React
 * scheduler.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var ic;function sf(){return ic||(ic=1,(function(s){function h(P,B){var F=P.length;P.push(B);e:for(;0<F;){var m=F-1>>>1,k=P[m];if(0<x(k,B))P[m]=B,P[F]=k,F=m;else break e}}function f(P){return P.length===0?null:P[0]}function w(P){if(P.length===0)return null;var B=P[0],F=P.pop();if(F!==B){P[0]=F;e:for(var m=0,k=P.length,q=k>>>1;m<q;){var J=2*(m+1)-1,ie=P[J],oe=J+1,he=P[oe];if(0>x(ie,F))oe<k&&0>x(he,ie)?(P[m]=he,P[oe]=F,m=oe):(P[m]=ie,P[J]=F,m=J);else if(oe<k&&0>x(he,F))P[m]=he,P[oe]=F,m=oe;else break e}}return B}function x(P,B){var F=P.sortIndex-B.sortIndex;return F!==0?F:P.id-B.id}if(typeof performance=="object"&&typeof performance.now=="function"){var E=performance;s.unstable_now=function(){return E.now()}}else{var L=Date,O=L.now();s.unstable_now=function(){return L.now()-O}}var U=[],le=[],X=1,K=null,ee=3,ve=!1,ne=!1,te=!1,H=typeof setTimeout=="function"?setTimeout:null,Fe=typeof clearTimeout=="function"?clearTimeout:null,we=typeof setImmediate<"u"?setImmediate:null;typeof navigator<"u"&&navigator.scheduling!==void 0&&navigator.scheduling.isInputPending!==void 0&&navigator.scheduling.isInputPending.bind(navigator.scheduling);function Ne(P){for(var B=f(le);B!==null;){if(B.callback===null)w(le);else if(B.startTime<=P)w(le),B.sortIndex=B.expirationTime,h(U,B);else break;B=f(le)}}function de(P){if(te=!1,Ne(P),!ne)if(f(U)!==null)ne=!0,se(Me);else{var B=f(le);B!==null&&G(de,B.startTime-P)}}function Me(P,B){ne=!1,te&&(te=!1,Fe(Ue),Ue=-1),ve=!0;var F=ee;try{for(Ne(B),K=f(U);K!==null&&(!(K.expirationTime>B)||P&&!$());){var m=K.callback;if(typeof m=="function"){K.callback=null,ee=K.priorityLevel;var k=m(K.expirationTime<=B);B=s.unstable_now(),typeof k=="function"?K.callback=k:K===f(U)&&w(U),Ne(B)}else w(U);K=f(U)}if(K!==null)var q=!0;else{var J=f(le);J!==null&&G(de,J.startTime-B),q=!1}return q}finally{K=null,ee=F,ve=!1}}var fe=!1,ke=null,Ue=-1,Ke=5,Ye=-1;function $(){return!(s.unstable_now()-Ye<Ke)}function ye(){if(ke!==null){var P=s.unstable_now();Ye=P;var B=!0;try{B=ke(!0,P)}finally{B?D():(fe=!1,ke=null)}}else fe=!1}var D;if(typeof we=="function")D=function(){we(ye)};else if(typeof MessageChannel<"u"){var Z=new MessageChannel,ae=Z.port2;Z.port1.onmessage=ye,D=function(){ae.postMessage(null)}}else D=function(){H(ye,0)};function se(P){ke=P,fe||(fe=!0,D())}function G(P,B){Ue=H(function(){P(s.unstable_now())},B)}s.unstable_IdlePriority=5,s.unstable_ImmediatePriority=1,s.unstable_LowPriority=4,s.unstable_NormalPriority=3,s.unstable_Profiling=null,s.unstable_UserBlockingPriority=2,s.unstable_cancelCallback=function(P){P.callback=null},s.unstable_continueExecution=function(){ne||ve||(ne=!0,se(Me))},s.unstable_forceFrameRate=function(P){0>P||125<P?console.error("forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported"):Ke=0<P?Math.floor(1e3/P):5},s.unstable_getCurrentPriorityLevel=function(){return ee},s.unstable_getFirstCallbackNode=function(){return f(U)},s.unstable_next=function(P){switch(ee){case 1:case 2:case 3:var B=3;break;default:B=ee}var F=ee;ee=B;try{return P()}finally{ee=F}},s.unstable_pauseExecution=function(){},s.unstable_requestPaint=function(){},s.unstable_runWithPriority=function(P,B){switch(P){case 1:case 2:case 3:case 4:case 5:break;default:P=3}var F=ee;ee=P;try{return B()}finally{ee=F}},s.unstable_scheduleCallback=function(P,B,F){var m=s.unstable_now();switch(typeof F=="object"&&F!==null?(F=F.delay,F=typeof F=="number"&&0<F?m+F:m):F=m,P){case 1:var k=-1;break;case 2:k=250;break;case 5:k=1073741823;break;case 4:k=1e4;break;default:k=5e3}return k=F+k,P={id:X++,callback:B,priorityLevel:P,startTime:F,expirationTime:k,sortIndex:-1},F>m?(P.sortIndex=F,h(le,P),f(U)===null&&P===f(le)&&(te?(Fe(Ue),Ue=-1):te=!0,G(de,F-m))):(P.sortIndex=k,h(U,P),ne||ve||(ne=!0,se(Me))),P},s.unstable_shouldYield=$,s.unstable_wrapCallback=function(P){var B=ee;return function(){var F=ee;ee=B;try{return P.apply(this,arguments)}finally{ee=F}}}})(Sa)),Sa}var lc;function uf(){return lc||(lc=1,ka.exports=sf()),ka.exports}/**
 * @license React
 * react-dom.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */var oc;function cf(){if(oc)return dt;oc=1;var s=_a(),h=uf();function f(e){for(var t="https://reactjs.org/docs/error-decoder.html?invariant="+e,n=1;n<arguments.length;n++)t+="&args[]="+encodeURIComponent(arguments[n]);return"Minified React error #"+e+"; visit "+t+" for the full message or use the non-minified dev environment for full errors and additional helpful warnings."}var w=new Set,x={};function E(e,t){L(e,t),L(e+"Capture",t)}function L(e,t){for(x[e]=t,e=0;e<t.length;e++)w.add(t[e])}var O=!(typeof window>"u"||typeof window.document>"u"||typeof window.document.createElement>"u"),U=Object.prototype.hasOwnProperty,le=/^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/,X={},K={};function ee(e){return U.call(K,e)?!0:U.call(X,e)?!1:le.test(e)?K[e]=!0:(X[e]=!0,!1)}function ve(e,t,n,r){if(n!==null&&n.type===0)return!1;switch(typeof t){case"function":case"symbol":return!0;case"boolean":return r?!1:n!==null?!n.acceptsBooleans:(e=e.toLowerCase().slice(0,5),e!=="data-"&&e!=="aria-");default:return!1}}function ne(e,t,n,r){if(t===null||typeof t>"u"||ve(e,t,n,r))return!0;if(r)return!1;if(n!==null)switch(n.type){case 3:return!t;case 4:return t===!1;case 5:return isNaN(t);case 6:return isNaN(t)||1>t}return!1}function te(e,t,n,r,i,l,a){this.acceptsBooleans=t===2||t===3||t===4,this.attributeName=r,this.attributeNamespace=i,this.mustUseProperty=n,this.propertyName=e,this.type=t,this.sanitizeURL=l,this.removeEmptyString=a}var H={};"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style".split(" ").forEach(function(e){H[e]=new te(e,0,!1,e,null,!1,!1)}),[["acceptCharset","accept-charset"],["className","class"],["htmlFor","for"],["httpEquiv","http-equiv"]].forEach(function(e){var t=e[0];H[t]=new te(t,1,!1,e[1],null,!1,!1)}),["contentEditable","draggable","spellCheck","value"].forEach(function(e){H[e]=new te(e,2,!1,e.toLowerCase(),null,!1,!1)}),["autoReverse","externalResourcesRequired","focusable","preserveAlpha"].forEach(function(e){H[e]=new te(e,2,!1,e,null,!1,!1)}),"allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope".split(" ").forEach(function(e){H[e]=new te(e,3,!1,e.toLowerCase(),null,!1,!1)}),["checked","multiple","muted","selected"].forEach(function(e){H[e]=new te(e,3,!0,e,null,!1,!1)}),["capture","download"].forEach(function(e){H[e]=new te(e,4,!1,e,null,!1,!1)}),["cols","rows","size","span"].forEach(function(e){H[e]=new te(e,6,!1,e,null,!1,!1)}),["rowSpan","start"].forEach(function(e){H[e]=new te(e,5,!1,e.toLowerCase(),null,!1,!1)});var Fe=/[\-:]([a-z])/g;function we(e){return e[1].toUpperCase()}"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height".split(" ").forEach(function(e){var t=e.replace(Fe,we);H[t]=new te(t,1,!1,e,null,!1,!1)}),"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type".split(" ").forEach(function(e){var t=e.replace(Fe,we);H[t]=new te(t,1,!1,e,"http://www.w3.org/1999/xlink",!1,!1)}),["xml:base","xml:lang","xml:space"].forEach(function(e){var t=e.replace(Fe,we);H[t]=new te(t,1,!1,e,"http://www.w3.org/XML/1998/namespace",!1,!1)}),["tabIndex","crossOrigin"].forEach(function(e){H[e]=new te(e,1,!1,e.toLowerCase(),null,!1,!1)}),H.xlinkHref=new te("xlinkHref",1,!1,"xlink:href","http://www.w3.org/1999/xlink",!0,!1),["src","href","action","formAction"].forEach(function(e){H[e]=new te(e,1,!1,e.toLowerCase(),null,!0,!0)});function Ne(e,t,n,r){var i=H.hasOwnProperty(t)?H[t]:null;(i!==null?i.type!==0:r||!(2<t.length)||t[0]!=="o"&&t[0]!=="O"||t[1]!=="n"&&t[1]!=="N")&&(ne(t,n,i,r)&&(n=null),r||i===null?ee(t)&&(n===null?e.removeAttribute(t):e.setAttribute(t,""+n)):i.mustUseProperty?e[i.propertyName]=n===null?i.type===3?!1:"":n:(t=i.attributeName,r=i.attributeNamespace,n===null?e.removeAttribute(t):(i=i.type,n=i===3||i===4&&n===!0?"":""+n,r?e.setAttributeNS(r,t,n):e.setAttribute(t,n))))}var de=s.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED,Me=Symbol.for("react.element"),fe=Symbol.for("react.portal"),ke=Symbol.for("react.fragment"),Ue=Symbol.for("react.strict_mode"),Ke=Symbol.for("react.profiler"),Ye=Symbol.for("react.provider"),$=Symbol.for("react.context"),ye=Symbol.for("react.forward_ref"),D=Symbol.for("react.suspense"),Z=Symbol.for("react.suspense_list"),ae=Symbol.for("react.memo"),se=Symbol.for("react.lazy"),G=Symbol.for("react.offscreen"),P=Symbol.iterator;function B(e){return e===null||typeof e!="object"?null:(e=P&&e[P]||e["@@iterator"],typeof e=="function"?e:null)}var F=Object.assign,m;function k(e){if(m===void 0)try{throw Error()}catch(n){var t=n.stack.trim().match(/\n( *(at )?)/);m=t&&t[1]||""}return`
`+m+e}var q=!1;function J(e,t){if(!e||q)return"";q=!0;var n=Error.prepareStackTrace;Error.prepareStackTrace=void 0;try{if(t)if(t=function(){throw Error()},Object.defineProperty(t.prototype,"props",{set:function(){throw Error()}}),typeof Reflect=="object"&&Reflect.construct){try{Reflect.construct(t,[])}catch(y){var r=y}Reflect.construct(e,[],t)}else{try{t.call()}catch(y){r=y}e.call(t.prototype)}else{try{throw Error()}catch(y){r=y}e()}}catch(y){if(y&&r&&typeof y.stack=="string"){for(var i=y.stack.split(`
`),l=r.stack.split(`
`),a=i.length-1,u=l.length-1;1<=a&&0<=u&&i[a]!==l[u];)u--;for(;1<=a&&0<=u;a--,u--)if(i[a]!==l[u]){if(a!==1||u!==1)do if(a--,u--,0>u||i[a]!==l[u]){var d=`
`+i[a].replace(" at new "," at ");return e.displayName&&d.includes("<anonymous>")&&(d=d.replace("<anonymous>",e.displayName)),d}while(1<=a&&0<=u);break}}}finally{q=!1,Error.prepareStackTrace=n}return(e=e?e.displayName||e.name:"")?k(e):""}function ie(e){switch(e.tag){case 5:return k(e.type);case 16:return k("Lazy");case 13:return k("Suspense");case 19:return k("SuspenseList");case 0:case 2:case 15:return e=J(e.type,!1),e;case 11:return e=J(e.type.render,!1),e;case 1:return e=J(e.type,!0),e;default:return""}}function oe(e){if(e==null)return null;if(typeof e=="function")return e.displayName||e.name||null;if(typeof e=="string")return e;switch(e){case ke:return"Fragment";case fe:return"Portal";case Ke:return"Profiler";case Ue:return"StrictMode";case D:return"Suspense";case Z:return"SuspenseList"}if(typeof e=="object")switch(e.$$typeof){case $:return(e.displayName||"Context")+".Consumer";case Ye:return(e._context.displayName||"Context")+".Provider";case ye:var t=e.render;return e=e.displayName,e||(e=t.displayName||t.name||"",e=e!==""?"ForwardRef("+e+")":"ForwardRef"),e;case ae:return t=e.displayName||null,t!==null?t:oe(e.type)||"Memo";case se:t=e._payload,e=e._init;try{return oe(e(t))}catch{}}return null}function he(e){var t=e.type;switch(e.tag){case 24:return"Cache";case 9:return(t.displayName||"Context")+".Consumer";case 10:return(t._context.displayName||"Context")+".Provider";case 18:return"DehydratedFragment";case 11:return e=t.render,e=e.displayName||e.name||"",t.displayName||(e!==""?"ForwardRef("+e+")":"ForwardRef");case 7:return"Fragment";case 5:return t;case 4:return"Portal";case 3:return"Root";case 6:return"Text";case 16:return oe(t);case 8:return t===Ue?"StrictMode":"Mode";case 22:return"Offscreen";case 12:return"Profiler";case 21:return"Scope";case 13:return"Suspense";case 19:return"SuspenseList";case 25:return"TracingMarker";case 1:case 0:case 17:case 2:case 14:case 15:if(typeof t=="function")return t.displayName||t.name||null;if(typeof t=="string")return t}return null}function pe(e){switch(typeof e){case"boolean":case"number":case"string":case"undefined":return e;case"object":return e;default:return""}}function Se(e){var t=e.type;return(e=e.nodeName)&&e.toLowerCase()==="input"&&(t==="checkbox"||t==="radio")}function Ge(e){var t=Se(e)?"checked":"value",n=Object.getOwnPropertyDescriptor(e.constructor.prototype,t),r=""+e[t];if(!e.hasOwnProperty(t)&&typeof n<"u"&&typeof n.get=="function"&&typeof n.set=="function"){var i=n.get,l=n.set;return Object.defineProperty(e,t,{configurable:!0,get:function(){return i.call(this)},set:function(a){r=""+a,l.call(this,a)}}),Object.defineProperty(e,t,{enumerable:n.enumerable}),{getValue:function(){return r},setValue:function(a){r=""+a},stopTracking:function(){e._valueTracker=null,delete e[t]}}}}function it(e){e._valueTracker||(e._valueTracker=Ge(e))}function Ln(e){if(!e)return!1;var t=e._valueTracker;if(!t)return!0;var n=t.getValue(),r="";return e&&(r=Se(e)?e.checked?"true":"false":e.value),e=r,e!==n?(t.setValue(e),!0):!1}function Be(e){if(e=e||(typeof document<"u"?document:void 0),typeof e>"u")return null;try{return e.activeElement||e.body}catch{return e.body}}function Pt(e,t){var n=t.checked;return F({},t,{defaultChecked:void 0,defaultValue:void 0,value:void 0,checked:n??e._wrapperState.initialChecked})}function qe(e,t){var n=t.defaultValue==null?"":t.defaultValue,r=t.checked!=null?t.checked:t.defaultChecked;n=pe(t.value!=null?t.value:n),e._wrapperState={initialChecked:r,initialValue:n,controlled:t.type==="checkbox"||t.type==="radio"?t.checked!=null:t.value!=null}}function Lt(e,t){t=t.checked,t!=null&&Ne(e,"checked",t,!1)}function yt(e,t){Lt(e,t);var n=pe(t.value),r=t.type;if(n!=null)r==="number"?(n===0&&e.value===""||e.value!=n)&&(e.value=""+n):e.value!==""+n&&(e.value=""+n);else if(r==="submit"||r==="reset"){e.removeAttribute("value");return}t.hasOwnProperty("value")?xt(e,t.type,n):t.hasOwnProperty("defaultValue")&&xt(e,t.type,pe(t.defaultValue)),t.checked==null&&t.defaultChecked!=null&&(e.defaultChecked=!!t.defaultChecked)}function Kt(e,t,n){if(t.hasOwnProperty("value")||t.hasOwnProperty("defaultValue")){var r=t.type;if(!(r!=="submit"&&r!=="reset"||t.value!==void 0&&t.value!==null))return;t=""+e._wrapperState.initialValue,n||t===e.value||(e.value=t),e.defaultValue=t}n=e.name,n!==""&&(e.name=""),e.defaultChecked=!!e._wrapperState.initialChecked,n!==""&&(e.name=n)}function xt(e,t,n){(t!=="number"||Be(e.ownerDocument)!==e)&&(n==null?e.defaultValue=""+e._wrapperState.initialValue:e.defaultValue!==""+n&&(e.defaultValue=""+n))}var Dt=Array.isArray;function ft(e,t,n,r){if(e=e.options,t){t={};for(var i=0;i<n.length;i++)t["$"+n[i]]=!0;for(n=0;n<e.length;n++)i=t.hasOwnProperty("$"+e[n].value),e[n].selected!==i&&(e[n].selected=i),i&&r&&(e[n].defaultSelected=!0)}else{for(n=""+pe(n),t=null,i=0;i<e.length;i++){if(e[i].value===n){e[i].selected=!0,r&&(e[i].defaultSelected=!0);return}t!==null||e[i].disabled||(t=e[i])}t!==null&&(t.selected=!0)}}function lt(e,t){if(t.dangerouslySetInnerHTML!=null)throw Error(f(91));return F({},t,{value:void 0,defaultValue:void 0,children:""+e._wrapperState.initialValue})}function qn(e,t){var n=t.value;if(n==null){if(n=t.children,t=t.defaultValue,n!=null){if(t!=null)throw Error(f(92));if(Dt(n)){if(1<n.length)throw Error(f(93));n=n[0]}t=n}t==null&&(t=""),n=t}e._wrapperState={initialValue:pe(n)}}function Xn(e,t){var n=pe(t.value),r=pe(t.defaultValue);n!=null&&(n=""+n,n!==e.value&&(e.value=n),t.defaultValue==null&&e.defaultValue!==n&&(e.defaultValue=n)),r!=null&&(e.defaultValue=""+r)}function sn(e){var t=e.textContent;t===e._wrapperState.initialValue&&t!==""&&t!==null&&(e.value=t)}function Zn(e){switch(e){case"svg":return"http://www.w3.org/2000/svg";case"math":return"http://www.w3.org/1998/Math/MathML";default:return"http://www.w3.org/1999/xhtml"}}function Dn(e,t){return e==null||e==="http://www.w3.org/1999/xhtml"?Zn(t):e==="http://www.w3.org/2000/svg"&&t==="foreignObject"?"http://www.w3.org/1999/xhtml":e}var Yt,Mn=(function(e){return typeof MSApp<"u"&&MSApp.execUnsafeLocalFunction?function(t,n,r,i){MSApp.execUnsafeLocalFunction(function(){return e(t,n,r,i)})}:e})(function(e,t){if(e.namespaceURI!=="http://www.w3.org/2000/svg"||"innerHTML"in e)e.innerHTML=t;else{for(Yt=Yt||document.createElement("div"),Yt.innerHTML="<svg>"+t.valueOf().toString()+"</svg>",t=Yt.firstChild;e.firstChild;)e.removeChild(e.firstChild);for(;t.firstChild;)e.appendChild(t.firstChild)}});function Gt(e,t){if(t){var n=e.firstChild;if(n&&n===e.lastChild&&n.nodeType===3){n.nodeValue=t;return}}e.textContent=t}var pt={animationIterationCount:!0,aspectRatio:!0,borderImageOutset:!0,borderImageSlice:!0,borderImageWidth:!0,boxFlex:!0,boxFlexGroup:!0,boxOrdinalGroup:!0,columnCount:!0,columns:!0,flex:!0,flexGrow:!0,flexPositive:!0,flexShrink:!0,flexNegative:!0,flexOrder:!0,gridArea:!0,gridRow:!0,gridRowEnd:!0,gridRowSpan:!0,gridRowStart:!0,gridColumn:!0,gridColumnEnd:!0,gridColumnSpan:!0,gridColumnStart:!0,fontWeight:!0,lineClamp:!0,lineHeight:!0,opacity:!0,order:!0,orphans:!0,tabSize:!0,widows:!0,zIndex:!0,zoom:!0,fillOpacity:!0,floodOpacity:!0,stopOpacity:!0,strokeDasharray:!0,strokeDashoffset:!0,strokeMiterlimit:!0,strokeOpacity:!0,strokeWidth:!0},Tn=["Webkit","ms","Moz","O"];Object.keys(pt).forEach(function(e){Tn.forEach(function(t){t=t+e.charAt(0).toUpperCase()+e.substring(1),pt[t]=pt[e]})});function jr(e,t,n){return t==null||typeof t=="boolean"||t===""?"":n||typeof t!="number"||t===0||pt.hasOwnProperty(e)&&pt[e]?(""+t).trim():t+"px"}function gi(e,t){e=e.style;for(var n in t)if(t.hasOwnProperty(n)){var r=n.indexOf("--")===0,i=jr(n,t[n],r);n==="float"&&(n="cssFloat"),r?e.setProperty(n,i):e[n]=i}}var La=F({menuitem:!0},{area:!0,base:!0,br:!0,col:!0,embed:!0,hr:!0,img:!0,input:!0,keygen:!0,link:!0,meta:!0,param:!0,source:!0,track:!0,wbr:!0});function vi(e,t){if(t){if(La[e]&&(t.children!=null||t.dangerouslySetInnerHTML!=null))throw Error(f(137,e));if(t.dangerouslySetInnerHTML!=null){if(t.children!=null)throw Error(f(60));if(typeof t.dangerouslySetInnerHTML!="object"||!("__html"in t.dangerouslySetInnerHTML))throw Error(f(61))}if(t.style!=null&&typeof t.style!="object")throw Error(f(62))}}function Nr(e,t){if(e.indexOf("-")===-1)return typeof t.is=="string";switch(e){case"annotation-xml":case"color-profile":case"font-face":case"font-face-src":case"font-face-uri":case"font-face-format":case"font-face-name":case"missing-glyph":return!1;default:return!0}}var Fn=null;function Rn(e){return e=e.target||e.srcElement||window,e.correspondingUseElement&&(e=e.correspondingUseElement),e.nodeType===3?e.parentNode:e}var Cr=null,Ut=null,xe=null;function zr(e){if(e=Kr(e)){if(typeof Cr!="function")throw Error(f(280));var t=e.stateNode;t&&(t=$i(t),Cr(e.stateNode,e.type,t))}}function qt(e){Ut?xe?xe.push(e):xe=[e]:Ut=e}function wt(){if(Ut){var e=Ut,t=xe;if(xe=Ut=null,zr(e),t)for(e=0;e<t.length;e++)zr(t[e])}}function yi(e,t){return e(t)}function xi(){}var Jn=!1;function wi(e,t,n){if(Jn)return e(t,n);Jn=!0;try{return yi(e,t,n)}finally{Jn=!1,(Ut!==null||xe!==null)&&(xi(),wt())}}function In(e,t){var n=e.stateNode;if(n===null)return null;var r=$i(n);if(r===null)return null;n=r[t];e:switch(t){case"onClick":case"onClickCapture":case"onDoubleClick":case"onDoubleClickCapture":case"onMouseDown":case"onMouseDownCapture":case"onMouseMove":case"onMouseMoveCapture":case"onMouseUp":case"onMouseUpCapture":case"onMouseEnter":(r=!r.disabled)||(e=e.type,r=!(e==="button"||e==="input"||e==="select"||e==="textarea")),e=!r;break e;default:e=!1}if(e)return null;if(n&&typeof n!="function")throw Error(f(231,t,typeof n));return n}var er=!1;if(O)try{var un={};Object.defineProperty(un,"passive",{get:function(){er=!0}}),window.addEventListener("test",un,un),window.removeEventListener("test",un,un)}catch{er=!1}function Fl(e,t,n,r,i,l,a,u,d){var y=Array.prototype.slice.call(arguments,3);try{t.apply(n,y)}catch(j){this.onError(j)}}var Bt=!1,kt=null,St=!1,Er=null,Rl={onError:function(e){Bt=!0,kt=e}};function Il(e,t,n,r,i,l,a,u,d){Bt=!1,kt=null,Fl.apply(Rl,arguments)}function ki(e,t,n,r,i,l,a,u,d){if(Il.apply(this,arguments),Bt){if(Bt){var y=kt;Bt=!1,kt=null}else throw Error(f(198));St||(St=!0,Er=y)}}function Vt(e){var t=e,n=e;if(e.alternate)for(;t.return;)t=t.return;else{e=t;do t=e,(t.flags&4098)!==0&&(n=t.return),e=t.return;while(e)}return t.tag===3?n:null}function Si(e){if(e.tag===13){var t=e.memoizedState;if(t===null&&(e=e.alternate,e!==null&&(t=e.memoizedState)),t!==null)return t.dehydrated}return null}function ji(e){if(Vt(e)!==e)throw Error(f(188))}function Ol(e){var t=e.alternate;if(!t){if(t=Vt(e),t===null)throw Error(f(188));return t!==e?null:e}for(var n=e,r=t;;){var i=n.return;if(i===null)break;var l=i.alternate;if(l===null){if(r=i.return,r!==null){n=r;continue}break}if(i.child===l.child){for(l=i.child;l;){if(l===n)return ji(i),e;if(l===r)return ji(i),t;l=l.sibling}throw Error(f(188))}if(n.return!==r.return)n=i,r=l;else{for(var a=!1,u=i.child;u;){if(u===n){a=!0,n=i,r=l;break}if(u===r){a=!0,r=i,n=l;break}u=u.sibling}if(!a){for(u=l.child;u;){if(u===n){a=!0,n=l,r=i;break}if(u===r){a=!0,r=l,n=i;break}u=u.sibling}if(!a)throw Error(f(189))}}if(n.alternate!==r)throw Error(f(190))}if(n.tag!==3)throw Error(f(188));return n.stateNode.current===n?e:t}function _r(e){return e=Ol(e),e!==null?Ni(e):null}function Ni(e){if(e.tag===5||e.tag===6)return e;for(e=e.child;e!==null;){var t=Ni(e);if(t!==null)return t;e=e.sibling}return null}var Ci=h.unstable_scheduleCallback,zi=h.unstable_cancelCallback,c=h.unstable_shouldYield,N=h.unstable_requestPaint,z=h.unstable_now,b=h.unstable_getCurrentPriorityLevel,ue=h.unstable_ImmediatePriority,tt=h.unstable_UserBlockingPriority,ze=h.unstable_NormalPriority,Xt=h.unstable_LowPriority,On=h.unstable_IdlePriority,cn=null,bt=null;function yc(e){if(bt&&typeof bt.onCommitFiberRoot=="function")try{bt.onCommitFiberRoot(cn,e,void 0,(e.current.flags&128)===128)}catch{}}var Mt=Math.clz32?Math.clz32:kc,xc=Math.log,wc=Math.LN2;function kc(e){return e>>>=0,e===0?32:31-(xc(e)/wc|0)|0}var Ei=64,_i=4194304;function Pr(e){switch(e&-e){case 1:return 1;case 2:return 2;case 4:return 4;case 8:return 8;case 16:return 16;case 32:return 32;case 64:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:return e&4194240;case 4194304:case 8388608:case 16777216:case 33554432:case 67108864:return e&130023424;case 134217728:return 134217728;case 268435456:return 268435456;case 536870912:return 536870912;case 1073741824:return 1073741824;default:return e}}function Pi(e,t){var n=e.pendingLanes;if(n===0)return 0;var r=0,i=e.suspendedLanes,l=e.pingedLanes,a=n&268435455;if(a!==0){var u=a&~i;u!==0?r=Pr(u):(l&=a,l!==0&&(r=Pr(l)))}else a=n&~i,a!==0?r=Pr(a):l!==0&&(r=Pr(l));if(r===0)return 0;if(t!==0&&t!==r&&(t&i)===0&&(i=r&-r,l=t&-t,i>=l||i===16&&(l&4194240)!==0))return t;if((r&4)!==0&&(r|=n&16),t=e.entangledLanes,t!==0)for(e=e.entanglements,t&=r;0<t;)n=31-Mt(t),i=1<<n,r|=e[n],t&=~i;return r}function Sc(e,t){switch(e){case 1:case 2:case 4:return t+250;case 8:case 16:case 32:case 64:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:return t+5e3;case 4194304:case 8388608:case 16777216:case 33554432:case 67108864:return-1;case 134217728:case 268435456:case 536870912:case 1073741824:return-1;default:return-1}}function jc(e,t){for(var n=e.suspendedLanes,r=e.pingedLanes,i=e.expirationTimes,l=e.pendingLanes;0<l;){var a=31-Mt(l),u=1<<a,d=i[a];d===-1?((u&n)===0||(u&r)!==0)&&(i[a]=Sc(u,t)):d<=t&&(e.expiredLanes|=u),l&=~u}}function Al(e){return e=e.pendingLanes&-1073741825,e!==0?e:e&1073741824?1073741824:0}function Da(){var e=Ei;return Ei<<=1,(Ei&4194240)===0&&(Ei=64),e}function Ul(e){for(var t=[],n=0;31>n;n++)t.push(e);return t}function Lr(e,t,n){e.pendingLanes|=t,t!==536870912&&(e.suspendedLanes=0,e.pingedLanes=0),e=e.eventTimes,t=31-Mt(t),e[t]=n}function Nc(e,t){var n=e.pendingLanes&~t;e.pendingLanes=t,e.suspendedLanes=0,e.pingedLanes=0,e.expiredLanes&=t,e.mutableReadLanes&=t,e.entangledLanes&=t,t=e.entanglements;var r=e.eventTimes;for(e=e.expirationTimes;0<n;){var i=31-Mt(n),l=1<<i;t[i]=0,r[i]=-1,e[i]=-1,n&=~l}}function Bl(e,t){var n=e.entangledLanes|=t;for(e=e.entanglements;n;){var r=31-Mt(n),i=1<<r;i&t|e[r]&t&&(e[r]|=t),n&=~i}}var ge=0;function Ma(e){return e&=-e,1<e?4<e?(e&268435455)!==0?16:536870912:4:1}var Ta,Vl,Fa,Ra,Ia,bl=!1,Li=[],dn=null,fn=null,pn=null,Dr=new Map,Mr=new Map,mn=[],Cc="mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(" ");function Oa(e,t){switch(e){case"focusin":case"focusout":dn=null;break;case"dragenter":case"dragleave":fn=null;break;case"mouseover":case"mouseout":pn=null;break;case"pointerover":case"pointerout":Dr.delete(t.pointerId);break;case"gotpointercapture":case"lostpointercapture":Mr.delete(t.pointerId)}}function Tr(e,t,n,r,i,l){return e===null||e.nativeEvent!==l?(e={blockedOn:t,domEventName:n,eventSystemFlags:r,nativeEvent:l,targetContainers:[i]},t!==null&&(t=Kr(t),t!==null&&Vl(t)),e):(e.eventSystemFlags|=r,t=e.targetContainers,i!==null&&t.indexOf(i)===-1&&t.push(i),e)}function zc(e,t,n,r,i){switch(t){case"focusin":return dn=Tr(dn,e,t,n,r,i),!0;case"dragenter":return fn=Tr(fn,e,t,n,r,i),!0;case"mouseover":return pn=Tr(pn,e,t,n,r,i),!0;case"pointerover":var l=i.pointerId;return Dr.set(l,Tr(Dr.get(l)||null,e,t,n,r,i)),!0;case"gotpointercapture":return l=i.pointerId,Mr.set(l,Tr(Mr.get(l)||null,e,t,n,r,i)),!0}return!1}function Aa(e){var t=An(e.target);if(t!==null){var n=Vt(t);if(n!==null){if(t=n.tag,t===13){if(t=Si(n),t!==null){e.blockedOn=t,Ia(e.priority,function(){Fa(n)});return}}else if(t===3&&n.stateNode.current.memoizedState.isDehydrated){e.blockedOn=n.tag===3?n.stateNode.containerInfo:null;return}}}e.blockedOn=null}function Di(e){if(e.blockedOn!==null)return!1;for(var t=e.targetContainers;0<t.length;){var n=Ql(e.domEventName,e.eventSystemFlags,t[0],e.nativeEvent);if(n===null){n=e.nativeEvent;var r=new n.constructor(n.type,n);Fn=r,n.target.dispatchEvent(r),Fn=null}else return t=Kr(n),t!==null&&Vl(t),e.blockedOn=n,!1;t.shift()}return!0}function Ua(e,t,n){Di(e)&&n.delete(t)}function Ec(){bl=!1,dn!==null&&Di(dn)&&(dn=null),fn!==null&&Di(fn)&&(fn=null),pn!==null&&Di(pn)&&(pn=null),Dr.forEach(Ua),Mr.forEach(Ua)}function Fr(e,t){e.blockedOn===t&&(e.blockedOn=null,bl||(bl=!0,h.unstable_scheduleCallback(h.unstable_NormalPriority,Ec)))}function Rr(e){function t(i){return Fr(i,e)}if(0<Li.length){Fr(Li[0],e);for(var n=1;n<Li.length;n++){var r=Li[n];r.blockedOn===e&&(r.blockedOn=null)}}for(dn!==null&&Fr(dn,e),fn!==null&&Fr(fn,e),pn!==null&&Fr(pn,e),Dr.forEach(t),Mr.forEach(t),n=0;n<mn.length;n++)r=mn[n],r.blockedOn===e&&(r.blockedOn=null);for(;0<mn.length&&(n=mn[0],n.blockedOn===null);)Aa(n),n.blockedOn===null&&mn.shift()}var tr=de.ReactCurrentBatchConfig,Mi=!0;function _c(e,t,n,r){var i=ge,l=tr.transition;tr.transition=null;try{ge=1,Wl(e,t,n,r)}finally{ge=i,tr.transition=l}}function Pc(e,t,n,r){var i=ge,l=tr.transition;tr.transition=null;try{ge=4,Wl(e,t,n,r)}finally{ge=i,tr.transition=l}}function Wl(e,t,n,r){if(Mi){var i=Ql(e,t,n,r);if(i===null)ao(e,t,r,Ti,n),Oa(e,r);else if(zc(i,e,t,n,r))r.stopPropagation();else if(Oa(e,r),t&4&&-1<Cc.indexOf(e)){for(;i!==null;){var l=Kr(i);if(l!==null&&Ta(l),l=Ql(e,t,n,r),l===null&&ao(e,t,r,Ti,n),l===i)break;i=l}i!==null&&r.stopPropagation()}else ao(e,t,r,null,n)}}var Ti=null;function Ql(e,t,n,r){if(Ti=null,e=Rn(r),e=An(e),e!==null)if(t=Vt(e),t===null)e=null;else if(n=t.tag,n===13){if(e=Si(t),e!==null)return e;e=null}else if(n===3){if(t.stateNode.current.memoizedState.isDehydrated)return t.tag===3?t.stateNode.containerInfo:null;e=null}else t!==e&&(e=null);return Ti=e,null}function Ba(e){switch(e){case"cancel":case"click":case"close":case"contextmenu":case"copy":case"cut":case"auxclick":case"dblclick":case"dragend":case"dragstart":case"drop":case"focusin":case"focusout":case"input":case"invalid":case"keydown":case"keypress":case"keyup":case"mousedown":case"mouseup":case"paste":case"pause":case"play":case"pointercancel":case"pointerdown":case"pointerup":case"ratechange":case"reset":case"resize":case"seeked":case"submit":case"touchcancel":case"touchend":case"touchstart":case"volumechange":case"change":case"selectionchange":case"textInput":case"compositionstart":case"compositionend":case"compositionupdate":case"beforeblur":case"afterblur":case"beforeinput":case"blur":case"fullscreenchange":case"focus":case"hashchange":case"popstate":case"select":case"selectstart":return 1;case"drag":case"dragenter":case"dragexit":case"dragleave":case"dragover":case"mousemove":case"mouseout":case"mouseover":case"pointermove":case"pointerout":case"pointerover":case"scroll":case"toggle":case"touchmove":case"wheel":case"mouseenter":case"mouseleave":case"pointerenter":case"pointerleave":return 4;case"message":switch(b()){case ue:return 1;case tt:return 4;case ze:case Xt:return 16;case On:return 536870912;default:return 16}default:return 16}}var hn=null,$l=null,Fi=null;function Va(){if(Fi)return Fi;var e,t=$l,n=t.length,r,i="value"in hn?hn.value:hn.textContent,l=i.length;for(e=0;e<n&&t[e]===i[e];e++);var a=n-e;for(r=1;r<=a&&t[n-r]===i[l-r];r++);return Fi=i.slice(e,1<r?1-r:void 0)}function Ri(e){var t=e.keyCode;return"charCode"in e?(e=e.charCode,e===0&&t===13&&(e=13)):e=t,e===10&&(e=13),32<=e||e===13?e:0}function Ii(){return!0}function ba(){return!1}function mt(e){function t(n,r,i,l,a){this._reactName=n,this._targetInst=i,this.type=r,this.nativeEvent=l,this.target=a,this.currentTarget=null;for(var u in e)e.hasOwnProperty(u)&&(n=e[u],this[u]=n?n(l):l[u]);return this.isDefaultPrevented=(l.defaultPrevented!=null?l.defaultPrevented:l.returnValue===!1)?Ii:ba,this.isPropagationStopped=ba,this}return F(t.prototype,{preventDefault:function(){this.defaultPrevented=!0;var n=this.nativeEvent;n&&(n.preventDefault?n.preventDefault():typeof n.returnValue!="unknown"&&(n.returnValue=!1),this.isDefaultPrevented=Ii)},stopPropagation:function(){var n=this.nativeEvent;n&&(n.stopPropagation?n.stopPropagation():typeof n.cancelBubble!="unknown"&&(n.cancelBubble=!0),this.isPropagationStopped=Ii)},persist:function(){},isPersistent:Ii}),t}var nr={eventPhase:0,bubbles:0,cancelable:0,timeStamp:function(e){return e.timeStamp||Date.now()},defaultPrevented:0,isTrusted:0},Hl=mt(nr),Ir=F({},nr,{view:0,detail:0}),Lc=mt(Ir),Kl,Yl,Or,Oi=F({},Ir,{screenX:0,screenY:0,clientX:0,clientY:0,pageX:0,pageY:0,ctrlKey:0,shiftKey:0,altKey:0,metaKey:0,getModifierState:ql,button:0,buttons:0,relatedTarget:function(e){return e.relatedTarget===void 0?e.fromElement===e.srcElement?e.toElement:e.fromElement:e.relatedTarget},movementX:function(e){return"movementX"in e?e.movementX:(e!==Or&&(Or&&e.type==="mousemove"?(Kl=e.screenX-Or.screenX,Yl=e.screenY-Or.screenY):Yl=Kl=0,Or=e),Kl)},movementY:function(e){return"movementY"in e?e.movementY:Yl}}),Wa=mt(Oi),Dc=F({},Oi,{dataTransfer:0}),Mc=mt(Dc),Tc=F({},Ir,{relatedTarget:0}),Gl=mt(Tc),Fc=F({},nr,{animationName:0,elapsedTime:0,pseudoElement:0}),Rc=mt(Fc),Ic=F({},nr,{clipboardData:function(e){return"clipboardData"in e?e.clipboardData:window.clipboardData}}),Oc=mt(Ic),Ac=F({},nr,{data:0}),Qa=mt(Ac),Uc={Esc:"Escape",Spacebar:" ",Left:"ArrowLeft",Up:"ArrowUp",Right:"ArrowRight",Down:"ArrowDown",Del:"Delete",Win:"OS",Menu:"ContextMenu",Apps:"ContextMenu",Scroll:"ScrollLock",MozPrintableKey:"Unidentified"},Bc={8:"Backspace",9:"Tab",12:"Clear",13:"Enter",16:"Shift",17:"Control",18:"Alt",19:"Pause",20:"CapsLock",27:"Escape",32:" ",33:"PageUp",34:"PageDown",35:"End",36:"Home",37:"ArrowLeft",38:"ArrowUp",39:"ArrowRight",40:"ArrowDown",45:"Insert",46:"Delete",112:"F1",113:"F2",114:"F3",115:"F4",116:"F5",117:"F6",118:"F7",119:"F8",120:"F9",121:"F10",122:"F11",123:"F12",144:"NumLock",145:"ScrollLock",224:"Meta"},Vc={Alt:"altKey",Control:"ctrlKey",Meta:"metaKey",Shift:"shiftKey"};function bc(e){var t=this.nativeEvent;return t.getModifierState?t.getModifierState(e):(e=Vc[e])?!!t[e]:!1}function ql(){return bc}var Wc=F({},Ir,{key:function(e){if(e.key){var t=Uc[e.key]||e.key;if(t!=="Unidentified")return t}return e.type==="keypress"?(e=Ri(e),e===13?"Enter":String.fromCharCode(e)):e.type==="keydown"||e.type==="keyup"?Bc[e.keyCode]||"Unidentified":""},code:0,location:0,ctrlKey:0,shiftKey:0,altKey:0,metaKey:0,repeat:0,locale:0,getModifierState:ql,charCode:function(e){return e.type==="keypress"?Ri(e):0},keyCode:function(e){return e.type==="keydown"||e.type==="keyup"?e.keyCode:0},which:function(e){return e.type==="keypress"?Ri(e):e.type==="keydown"||e.type==="keyup"?e.keyCode:0}}),Qc=mt(Wc),$c=F({},Oi,{pointerId:0,width:0,height:0,pressure:0,tangentialPressure:0,tiltX:0,tiltY:0,twist:0,pointerType:0,isPrimary:0}),$a=mt($c),Hc=F({},Ir,{touches:0,targetTouches:0,changedTouches:0,altKey:0,metaKey:0,ctrlKey:0,shiftKey:0,getModifierState:ql}),Kc=mt(Hc),Yc=F({},nr,{propertyName:0,elapsedTime:0,pseudoElement:0}),Gc=mt(Yc),qc=F({},Oi,{deltaX:function(e){return"deltaX"in e?e.deltaX:"wheelDeltaX"in e?-e.wheelDeltaX:0},deltaY:function(e){return"deltaY"in e?e.deltaY:"wheelDeltaY"in e?-e.wheelDeltaY:"wheelDelta"in e?-e.wheelDelta:0},deltaZ:0,deltaMode:0}),Xc=mt(qc),Zc=[9,13,27,32],Xl=O&&"CompositionEvent"in window,Ar=null;O&&"documentMode"in document&&(Ar=document.documentMode);var Jc=O&&"TextEvent"in window&&!Ar,Ha=O&&(!Xl||Ar&&8<Ar&&11>=Ar),Ka=" ",Ya=!1;function Ga(e,t){switch(e){case"keyup":return Zc.indexOf(t.keyCode)!==-1;case"keydown":return t.keyCode!==229;case"keypress":case"mousedown":case"focusout":return!0;default:return!1}}function qa(e){return e=e.detail,typeof e=="object"&&"data"in e?e.data:null}var rr=!1;function ed(e,t){switch(e){case"compositionend":return qa(t);case"keypress":return t.which!==32?null:(Ya=!0,Ka);case"textInput":return e=t.data,e===Ka&&Ya?null:e;default:return null}}function td(e,t){if(rr)return e==="compositionend"||!Xl&&Ga(e,t)?(e=Va(),Fi=$l=hn=null,rr=!1,e):null;switch(e){case"paste":return null;case"keypress":if(!(t.ctrlKey||t.altKey||t.metaKey)||t.ctrlKey&&t.altKey){if(t.char&&1<t.char.length)return t.char;if(t.which)return String.fromCharCode(t.which)}return null;case"compositionend":return Ha&&t.locale!=="ko"?null:t.data;default:return null}}var nd={color:!0,date:!0,datetime:!0,"datetime-local":!0,email:!0,month:!0,number:!0,password:!0,range:!0,search:!0,tel:!0,text:!0,time:!0,url:!0,week:!0};function Xa(e){var t=e&&e.nodeName&&e.nodeName.toLowerCase();return t==="input"?!!nd[e.type]:t==="textarea"}function Za(e,t,n,r){qt(r),t=bi(t,"onChange"),0<t.length&&(n=new Hl("onChange","change",null,n,r),e.push({event:n,listeners:t}))}var Ur=null,Br=null;function rd(e){gs(e,0)}function Ai(e){var t=sr(e);if(Ln(t))return e}function id(e,t){if(e==="change")return t}var Ja=!1;if(O){var Zl;if(O){var Jl="oninput"in document;if(!Jl){var es=document.createElement("div");es.setAttribute("oninput","return;"),Jl=typeof es.oninput=="function"}Zl=Jl}else Zl=!1;Ja=Zl&&(!document.documentMode||9<document.documentMode)}function ts(){Ur&&(Ur.detachEvent("onpropertychange",ns),Br=Ur=null)}function ns(e){if(e.propertyName==="value"&&Ai(Br)){var t=[];Za(t,Br,e,Rn(e)),wi(rd,t)}}function ld(e,t,n){e==="focusin"?(ts(),Ur=t,Br=n,Ur.attachEvent("onpropertychange",ns)):e==="focusout"&&ts()}function od(e){if(e==="selectionchange"||e==="keyup"||e==="keydown")return Ai(Br)}function ad(e,t){if(e==="click")return Ai(t)}function sd(e,t){if(e==="input"||e==="change")return Ai(t)}function ud(e,t){return e===t&&(e!==0||1/e===1/t)||e!==e&&t!==t}var Tt=typeof Object.is=="function"?Object.is:ud;function Vr(e,t){if(Tt(e,t))return!0;if(typeof e!="object"||e===null||typeof t!="object"||t===null)return!1;var n=Object.keys(e),r=Object.keys(t);if(n.length!==r.length)return!1;for(r=0;r<n.length;r++){var i=n[r];if(!U.call(t,i)||!Tt(e[i],t[i]))return!1}return!0}function rs(e){for(;e&&e.firstChild;)e=e.firstChild;return e}function is(e,t){var n=rs(e);e=0;for(var r;n;){if(n.nodeType===3){if(r=e+n.textContent.length,e<=t&&r>=t)return{node:n,offset:t-e};e=r}e:{for(;n;){if(n.nextSibling){n=n.nextSibling;break e}n=n.parentNode}n=void 0}n=rs(n)}}function ls(e,t){return e&&t?e===t?!0:e&&e.nodeType===3?!1:t&&t.nodeType===3?ls(e,t.parentNode):"contains"in e?e.contains(t):e.compareDocumentPosition?!!(e.compareDocumentPosition(t)&16):!1:!1}function os(){for(var e=window,t=Be();t instanceof e.HTMLIFrameElement;){try{var n=typeof t.contentWindow.location.href=="string"}catch{n=!1}if(n)e=t.contentWindow;else break;t=Be(e.document)}return t}function eo(e){var t=e&&e.nodeName&&e.nodeName.toLowerCase();return t&&(t==="input"&&(e.type==="text"||e.type==="search"||e.type==="tel"||e.type==="url"||e.type==="password")||t==="textarea"||e.contentEditable==="true")}function cd(e){var t=os(),n=e.focusedElem,r=e.selectionRange;if(t!==n&&n&&n.ownerDocument&&ls(n.ownerDocument.documentElement,n)){if(r!==null&&eo(n)){if(t=r.start,e=r.end,e===void 0&&(e=t),"selectionStart"in n)n.selectionStart=t,n.selectionEnd=Math.min(e,n.value.length);else if(e=(t=n.ownerDocument||document)&&t.defaultView||window,e.getSelection){e=e.getSelection();var i=n.textContent.length,l=Math.min(r.start,i);r=r.end===void 0?l:Math.min(r.end,i),!e.extend&&l>r&&(i=r,r=l,l=i),i=is(n,l);var a=is(n,r);i&&a&&(e.rangeCount!==1||e.anchorNode!==i.node||e.anchorOffset!==i.offset||e.focusNode!==a.node||e.focusOffset!==a.offset)&&(t=t.createRange(),t.setStart(i.node,i.offset),e.removeAllRanges(),l>r?(e.addRange(t),e.extend(a.node,a.offset)):(t.setEnd(a.node,a.offset),e.addRange(t)))}}for(t=[],e=n;e=e.parentNode;)e.nodeType===1&&t.push({element:e,left:e.scrollLeft,top:e.scrollTop});for(typeof n.focus=="function"&&n.focus(),n=0;n<t.length;n++)e=t[n],e.element.scrollLeft=e.left,e.element.scrollTop=e.top}}var dd=O&&"documentMode"in document&&11>=document.documentMode,ir=null,to=null,br=null,no=!1;function as(e,t,n){var r=n.window===n?n.document:n.nodeType===9?n:n.ownerDocument;no||ir==null||ir!==Be(r)||(r=ir,"selectionStart"in r&&eo(r)?r={start:r.selectionStart,end:r.selectionEnd}:(r=(r.ownerDocument&&r.ownerDocument.defaultView||window).getSelection(),r={anchorNode:r.anchorNode,anchorOffset:r.anchorOffset,focusNode:r.focusNode,focusOffset:r.focusOffset}),br&&Vr(br,r)||(br=r,r=bi(to,"onSelect"),0<r.length&&(t=new Hl("onSelect","select",null,t,n),e.push({event:t,listeners:r}),t.target=ir)))}function Ui(e,t){var n={};return n[e.toLowerCase()]=t.toLowerCase(),n["Webkit"+e]="webkit"+t,n["Moz"+e]="moz"+t,n}var lr={animationend:Ui("Animation","AnimationEnd"),animationiteration:Ui("Animation","AnimationIteration"),animationstart:Ui("Animation","AnimationStart"),transitionend:Ui("Transition","TransitionEnd")},ro={},ss={};O&&(ss=document.createElement("div").style,"AnimationEvent"in window||(delete lr.animationend.animation,delete lr.animationiteration.animation,delete lr.animationstart.animation),"TransitionEvent"in window||delete lr.transitionend.transition);function Bi(e){if(ro[e])return ro[e];if(!lr[e])return e;var t=lr[e],n;for(n in t)if(t.hasOwnProperty(n)&&n in ss)return ro[e]=t[n];return e}var us=Bi("animationend"),cs=Bi("animationiteration"),ds=Bi("animationstart"),fs=Bi("transitionend"),ps=new Map,ms="abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(" ");function gn(e,t){ps.set(e,t),E(t,[e])}for(var io=0;io<ms.length;io++){var lo=ms[io],fd=lo.toLowerCase(),pd=lo[0].toUpperCase()+lo.slice(1);gn(fd,"on"+pd)}gn(us,"onAnimationEnd"),gn(cs,"onAnimationIteration"),gn(ds,"onAnimationStart"),gn("dblclick","onDoubleClick"),gn("focusin","onFocus"),gn("focusout","onBlur"),gn(fs,"onTransitionEnd"),L("onMouseEnter",["mouseout","mouseover"]),L("onMouseLeave",["mouseout","mouseover"]),L("onPointerEnter",["pointerout","pointerover"]),L("onPointerLeave",["pointerout","pointerover"]),E("onChange","change click focusin focusout input keydown keyup selectionchange".split(" ")),E("onSelect","focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" ")),E("onBeforeInput",["compositionend","keypress","textInput","paste"]),E("onCompositionEnd","compositionend focusout keydown keypress keyup mousedown".split(" ")),E("onCompositionStart","compositionstart focusout keydown keypress keyup mousedown".split(" ")),E("onCompositionUpdate","compositionupdate focusout keydown keypress keyup mousedown".split(" "));var Wr="abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(" "),md=new Set("cancel close invalid load scroll toggle".split(" ").concat(Wr));function hs(e,t,n){var r=e.type||"unknown-event";e.currentTarget=n,ki(r,t,void 0,e),e.currentTarget=null}function gs(e,t){t=(t&4)!==0;for(var n=0;n<e.length;n++){var r=e[n],i=r.event;r=r.listeners;e:{var l=void 0;if(t)for(var a=r.length-1;0<=a;a--){var u=r[a],d=u.instance,y=u.currentTarget;if(u=u.listener,d!==l&&i.isPropagationStopped())break e;hs(i,u,y),l=d}else for(a=0;a<r.length;a++){if(u=r[a],d=u.instance,y=u.currentTarget,u=u.listener,d!==l&&i.isPropagationStopped())break e;hs(i,u,y),l=d}}}if(St)throw e=Er,St=!1,Er=null,e}function Ee(e,t){var n=t[mo];n===void 0&&(n=t[mo]=new Set);var r=e+"__bubble";n.has(r)||(vs(t,e,2,!1),n.add(r))}function oo(e,t,n){var r=0;t&&(r|=4),vs(n,e,r,t)}var Vi="_reactListening"+Math.random().toString(36).slice(2);function Qr(e){if(!e[Vi]){e[Vi]=!0,w.forEach(function(n){n!=="selectionchange"&&(md.has(n)||oo(n,!1,e),oo(n,!0,e))});var t=e.nodeType===9?e:e.ownerDocument;t===null||t[Vi]||(t[Vi]=!0,oo("selectionchange",!1,t))}}function vs(e,t,n,r){switch(Ba(t)){case 1:var i=_c;break;case 4:i=Pc;break;default:i=Wl}n=i.bind(null,t,n,e),i=void 0,!er||t!=="touchstart"&&t!=="touchmove"&&t!=="wheel"||(i=!0),r?i!==void 0?e.addEventListener(t,n,{capture:!0,passive:i}):e.addEventListener(t,n,!0):i!==void 0?e.addEventListener(t,n,{passive:i}):e.addEventListener(t,n,!1)}function ao(e,t,n,r,i){var l=r;if((t&1)===0&&(t&2)===0&&r!==null)e:for(;;){if(r===null)return;var a=r.tag;if(a===3||a===4){var u=r.stateNode.containerInfo;if(u===i||u.nodeType===8&&u.parentNode===i)break;if(a===4)for(a=r.return;a!==null;){var d=a.tag;if((d===3||d===4)&&(d=a.stateNode.containerInfo,d===i||d.nodeType===8&&d.parentNode===i))return;a=a.return}for(;u!==null;){if(a=An(u),a===null)return;if(d=a.tag,d===5||d===6){r=l=a;continue e}u=u.parentNode}}r=r.return}wi(function(){var y=l,j=Rn(n),C=[];e:{var S=ps.get(e);if(S!==void 0){var M=Hl,I=e;switch(e){case"keypress":if(Ri(n)===0)break e;case"keydown":case"keyup":M=Qc;break;case"focusin":I="focus",M=Gl;break;case"focusout":I="blur",M=Gl;break;case"beforeblur":case"afterblur":M=Gl;break;case"click":if(n.button===2)break e;case"auxclick":case"dblclick":case"mousedown":case"mousemove":case"mouseup":case"mouseout":case"mouseover":case"contextmenu":M=Wa;break;case"drag":case"dragend":case"dragenter":case"dragexit":case"dragleave":case"dragover":case"dragstart":case"drop":M=Mc;break;case"touchcancel":case"touchend":case"touchmove":case"touchstart":M=Kc;break;case us:case cs:case ds:M=Rc;break;case fs:M=Gc;break;case"scroll":M=Lc;break;case"wheel":M=Xc;break;case"copy":case"cut":case"paste":M=Oc;break;case"gotpointercapture":case"lostpointercapture":case"pointercancel":case"pointerdown":case"pointermove":case"pointerout":case"pointerover":case"pointerup":M=$a}var A=(t&4)!==0,Re=!A&&e==="scroll",g=A?S!==null?S+"Capture":null:S;A=[];for(var p=y,v;p!==null;){v=p;var _=v.stateNode;if(v.tag===5&&_!==null&&(v=_,g!==null&&(_=In(p,g),_!=null&&A.push($r(p,_,v)))),Re)break;p=p.return}0<A.length&&(S=new M(S,I,null,n,j),C.push({event:S,listeners:A}))}}if((t&7)===0){e:{if(S=e==="mouseover"||e==="pointerover",M=e==="mouseout"||e==="pointerout",S&&n!==Fn&&(I=n.relatedTarget||n.fromElement)&&(An(I)||I[Zt]))break e;if((M||S)&&(S=j.window===j?j:(S=j.ownerDocument)?S.defaultView||S.parentWindow:window,M?(I=n.relatedTarget||n.toElement,M=y,I=I?An(I):null,I!==null&&(Re=Vt(I),I!==Re||I.tag!==5&&I.tag!==6)&&(I=null)):(M=null,I=y),M!==I)){if(A=Wa,_="onMouseLeave",g="onMouseEnter",p="mouse",(e==="pointerout"||e==="pointerover")&&(A=$a,_="onPointerLeave",g="onPointerEnter",p="pointer"),Re=M==null?S:sr(M),v=I==null?S:sr(I),S=new A(_,p+"leave",M,n,j),S.target=Re,S.relatedTarget=v,_=null,An(j)===y&&(A=new A(g,p+"enter",I,n,j),A.target=v,A.relatedTarget=Re,_=A),Re=_,M&&I)t:{for(A=M,g=I,p=0,v=A;v;v=or(v))p++;for(v=0,_=g;_;_=or(_))v++;for(;0<p-v;)A=or(A),p--;for(;0<v-p;)g=or(g),v--;for(;p--;){if(A===g||g!==null&&A===g.alternate)break t;A=or(A),g=or(g)}A=null}else A=null;M!==null&&ys(C,S,M,A,!1),I!==null&&Re!==null&&ys(C,Re,I,A,!0)}}e:{if(S=y?sr(y):window,M=S.nodeName&&S.nodeName.toLowerCase(),M==="select"||M==="input"&&S.type==="file")var V=id;else if(Xa(S))if(Ja)V=sd;else{V=od;var W=ld}else(M=S.nodeName)&&M.toLowerCase()==="input"&&(S.type==="checkbox"||S.type==="radio")&&(V=ad);if(V&&(V=V(e,y))){Za(C,V,n,j);break e}W&&W(e,S,y),e==="focusout"&&(W=S._wrapperState)&&W.controlled&&S.type==="number"&&xt(S,"number",S.value)}switch(W=y?sr(y):window,e){case"focusin":(Xa(W)||W.contentEditable==="true")&&(ir=W,to=y,br=null);break;case"focusout":br=to=ir=null;break;case"mousedown":no=!0;break;case"contextmenu":case"mouseup":case"dragend":no=!1,as(C,n,j);break;case"selectionchange":if(dd)break;case"keydown":case"keyup":as(C,n,j)}var Q;if(Xl)e:{switch(e){case"compositionstart":var Y="onCompositionStart";break e;case"compositionend":Y="onCompositionEnd";break e;case"compositionupdate":Y="onCompositionUpdate";break e}Y=void 0}else rr?Ga(e,n)&&(Y="onCompositionEnd"):e==="keydown"&&n.keyCode===229&&(Y="onCompositionStart");Y&&(Ha&&n.locale!=="ko"&&(rr||Y!=="onCompositionStart"?Y==="onCompositionEnd"&&rr&&(Q=Va()):(hn=j,$l="value"in hn?hn.value:hn.textContent,rr=!0)),W=bi(y,Y),0<W.length&&(Y=new Qa(Y,e,null,n,j),C.push({event:Y,listeners:W}),Q?Y.data=Q:(Q=qa(n),Q!==null&&(Y.data=Q)))),(Q=Jc?ed(e,n):td(e,n))&&(y=bi(y,"onBeforeInput"),0<y.length&&(j=new Qa("onBeforeInput","beforeinput",null,n,j),C.push({event:j,listeners:y}),j.data=Q))}gs(C,t)})}function $r(e,t,n){return{instance:e,listener:t,currentTarget:n}}function bi(e,t){for(var n=t+"Capture",r=[];e!==null;){var i=e,l=i.stateNode;i.tag===5&&l!==null&&(i=l,l=In(e,n),l!=null&&r.unshift($r(e,l,i)),l=In(e,t),l!=null&&r.push($r(e,l,i))),e=e.return}return r}function or(e){if(e===null)return null;do e=e.return;while(e&&e.tag!==5);return e||null}function ys(e,t,n,r,i){for(var l=t._reactName,a=[];n!==null&&n!==r;){var u=n,d=u.alternate,y=u.stateNode;if(d!==null&&d===r)break;u.tag===5&&y!==null&&(u=y,i?(d=In(n,l),d!=null&&a.unshift($r(n,d,u))):i||(d=In(n,l),d!=null&&a.push($r(n,d,u)))),n=n.return}a.length!==0&&e.push({event:t,listeners:a})}var hd=/\r\n?/g,gd=/\u0000|\uFFFD/g;function xs(e){return(typeof e=="string"?e:""+e).replace(hd,`
`).replace(gd,"")}function Wi(e,t,n){if(t=xs(t),xs(e)!==t&&n)throw Error(f(425))}function Qi(){}var so=null,uo=null;function co(e,t){return e==="textarea"||e==="noscript"||typeof t.children=="string"||typeof t.children=="number"||typeof t.dangerouslySetInnerHTML=="object"&&t.dangerouslySetInnerHTML!==null&&t.dangerouslySetInnerHTML.__html!=null}var fo=typeof setTimeout=="function"?setTimeout:void 0,vd=typeof clearTimeout=="function"?clearTimeout:void 0,ws=typeof Promise=="function"?Promise:void 0,yd=typeof queueMicrotask=="function"?queueMicrotask:typeof ws<"u"?function(e){return ws.resolve(null).then(e).catch(xd)}:fo;function xd(e){setTimeout(function(){throw e})}function po(e,t){var n=t,r=0;do{var i=n.nextSibling;if(e.removeChild(n),i&&i.nodeType===8)if(n=i.data,n==="/$"){if(r===0){e.removeChild(i),Rr(t);return}r--}else n!=="$"&&n!=="$?"&&n!=="$!"||r++;n=i}while(n);Rr(t)}function vn(e){for(;e!=null;e=e.nextSibling){var t=e.nodeType;if(t===1||t===3)break;if(t===8){if(t=e.data,t==="$"||t==="$!"||t==="$?")break;if(t==="/$")return null}}return e}function ks(e){e=e.previousSibling;for(var t=0;e;){if(e.nodeType===8){var n=e.data;if(n==="$"||n==="$!"||n==="$?"){if(t===0)return e;t--}else n==="/$"&&t++}e=e.previousSibling}return null}var ar=Math.random().toString(36).slice(2),Wt="__reactFiber$"+ar,Hr="__reactProps$"+ar,Zt="__reactContainer$"+ar,mo="__reactEvents$"+ar,wd="__reactListeners$"+ar,kd="__reactHandles$"+ar;function An(e){var t=e[Wt];if(t)return t;for(var n=e.parentNode;n;){if(t=n[Zt]||n[Wt]){if(n=t.alternate,t.child!==null||n!==null&&n.child!==null)for(e=ks(e);e!==null;){if(n=e[Wt])return n;e=ks(e)}return t}e=n,n=e.parentNode}return null}function Kr(e){return e=e[Wt]||e[Zt],!e||e.tag!==5&&e.tag!==6&&e.tag!==13&&e.tag!==3?null:e}function sr(e){if(e.tag===5||e.tag===6)return e.stateNode;throw Error(f(33))}function $i(e){return e[Hr]||null}var ho=[],ur=-1;function yn(e){return{current:e}}function _e(e){0>ur||(e.current=ho[ur],ho[ur]=null,ur--)}function Ce(e,t){ur++,ho[ur]=e.current,e.current=t}var xn={},Xe=yn(xn),ot=yn(!1),Un=xn;function cr(e,t){var n=e.type.contextTypes;if(!n)return xn;var r=e.stateNode;if(r&&r.__reactInternalMemoizedUnmaskedChildContext===t)return r.__reactInternalMemoizedMaskedChildContext;var i={},l;for(l in n)i[l]=t[l];return r&&(e=e.stateNode,e.__reactInternalMemoizedUnmaskedChildContext=t,e.__reactInternalMemoizedMaskedChildContext=i),i}function at(e){return e=e.childContextTypes,e!=null}function Hi(){_e(ot),_e(Xe)}function Ss(e,t,n){if(Xe.current!==xn)throw Error(f(168));Ce(Xe,t),Ce(ot,n)}function js(e,t,n){var r=e.stateNode;if(t=t.childContextTypes,typeof r.getChildContext!="function")return n;r=r.getChildContext();for(var i in r)if(!(i in t))throw Error(f(108,he(e)||"Unknown",i));return F({},n,r)}function Ki(e){return e=(e=e.stateNode)&&e.__reactInternalMemoizedMergedChildContext||xn,Un=Xe.current,Ce(Xe,e),Ce(ot,ot.current),!0}function Ns(e,t,n){var r=e.stateNode;if(!r)throw Error(f(169));n?(e=js(e,t,Un),r.__reactInternalMemoizedMergedChildContext=e,_e(ot),_e(Xe),Ce(Xe,e)):_e(ot),Ce(ot,n)}var Jt=null,Yi=!1,go=!1;function Cs(e){Jt===null?Jt=[e]:Jt.push(e)}function Sd(e){Yi=!0,Cs(e)}function wn(){if(!go&&Jt!==null){go=!0;var e=0,t=ge;try{var n=Jt;for(ge=1;e<n.length;e++){var r=n[e];do r=r(!0);while(r!==null)}Jt=null,Yi=!1}catch(i){throw Jt!==null&&(Jt=Jt.slice(e+1)),Ci(ue,wn),i}finally{ge=t,go=!1}}return null}var dr=[],fr=0,Gi=null,qi=0,jt=[],Nt=0,Bn=null,en=1,tn="";function Vn(e,t){dr[fr++]=qi,dr[fr++]=Gi,Gi=e,qi=t}function zs(e,t,n){jt[Nt++]=en,jt[Nt++]=tn,jt[Nt++]=Bn,Bn=e;var r=en;e=tn;var i=32-Mt(r)-1;r&=~(1<<i),n+=1;var l=32-Mt(t)+i;if(30<l){var a=i-i%5;l=(r&(1<<a)-1).toString(32),r>>=a,i-=a,en=1<<32-Mt(t)+i|n<<i|r,tn=l+e}else en=1<<l|n<<i|r,tn=e}function vo(e){e.return!==null&&(Vn(e,1),zs(e,1,0))}function yo(e){for(;e===Gi;)Gi=dr[--fr],dr[fr]=null,qi=dr[--fr],dr[fr]=null;for(;e===Bn;)Bn=jt[--Nt],jt[Nt]=null,tn=jt[--Nt],jt[Nt]=null,en=jt[--Nt],jt[Nt]=null}var ht=null,gt=null,Pe=!1,Ft=null;function Es(e,t){var n=_t(5,null,null,0);n.elementType="DELETED",n.stateNode=t,n.return=e,t=e.deletions,t===null?(e.deletions=[n],e.flags|=16):t.push(n)}function _s(e,t){switch(e.tag){case 5:var n=e.type;return t=t.nodeType!==1||n.toLowerCase()!==t.nodeName.toLowerCase()?null:t,t!==null?(e.stateNode=t,ht=e,gt=vn(t.firstChild),!0):!1;case 6:return t=e.pendingProps===""||t.nodeType!==3?null:t,t!==null?(e.stateNode=t,ht=e,gt=null,!0):!1;case 13:return t=t.nodeType!==8?null:t,t!==null?(n=Bn!==null?{id:en,overflow:tn}:null,e.memoizedState={dehydrated:t,treeContext:n,retryLane:1073741824},n=_t(18,null,null,0),n.stateNode=t,n.return=e,e.child=n,ht=e,gt=null,!0):!1;default:return!1}}function xo(e){return(e.mode&1)!==0&&(e.flags&128)===0}function wo(e){if(Pe){var t=gt;if(t){var n=t;if(!_s(e,t)){if(xo(e))throw Error(f(418));t=vn(n.nextSibling);var r=ht;t&&_s(e,t)?Es(r,n):(e.flags=e.flags&-4097|2,Pe=!1,ht=e)}}else{if(xo(e))throw Error(f(418));e.flags=e.flags&-4097|2,Pe=!1,ht=e}}}function Ps(e){for(e=e.return;e!==null&&e.tag!==5&&e.tag!==3&&e.tag!==13;)e=e.return;ht=e}function Xi(e){if(e!==ht)return!1;if(!Pe)return Ps(e),Pe=!0,!1;var t;if((t=e.tag!==3)&&!(t=e.tag!==5)&&(t=e.type,t=t!=="head"&&t!=="body"&&!co(e.type,e.memoizedProps)),t&&(t=gt)){if(xo(e))throw Ls(),Error(f(418));for(;t;)Es(e,t),t=vn(t.nextSibling)}if(Ps(e),e.tag===13){if(e=e.memoizedState,e=e!==null?e.dehydrated:null,!e)throw Error(f(317));e:{for(e=e.nextSibling,t=0;e;){if(e.nodeType===8){var n=e.data;if(n==="/$"){if(t===0){gt=vn(e.nextSibling);break e}t--}else n!=="$"&&n!=="$!"&&n!=="$?"||t++}e=e.nextSibling}gt=null}}else gt=ht?vn(e.stateNode.nextSibling):null;return!0}function Ls(){for(var e=gt;e;)e=vn(e.nextSibling)}function pr(){gt=ht=null,Pe=!1}function ko(e){Ft===null?Ft=[e]:Ft.push(e)}var jd=de.ReactCurrentBatchConfig;function Yr(e,t,n){if(e=n.ref,e!==null&&typeof e!="function"&&typeof e!="object"){if(n._owner){if(n=n._owner,n){if(n.tag!==1)throw Error(f(309));var r=n.stateNode}if(!r)throw Error(f(147,e));var i=r,l=""+e;return t!==null&&t.ref!==null&&typeof t.ref=="function"&&t.ref._stringRef===l?t.ref:(t=function(a){var u=i.refs;a===null?delete u[l]:u[l]=a},t._stringRef=l,t)}if(typeof e!="string")throw Error(f(284));if(!n._owner)throw Error(f(290,e))}return e}function Zi(e,t){throw e=Object.prototype.toString.call(t),Error(f(31,e==="[object Object]"?"object with keys {"+Object.keys(t).join(", ")+"}":e))}function Ds(e){var t=e._init;return t(e._payload)}function Ms(e){function t(g,p){if(e){var v=g.deletions;v===null?(g.deletions=[p],g.flags|=16):v.push(p)}}function n(g,p){if(!e)return null;for(;p!==null;)t(g,p),p=p.sibling;return null}function r(g,p){for(g=new Map;p!==null;)p.key!==null?g.set(p.key,p):g.set(p.index,p),p=p.sibling;return g}function i(g,p){return g=_n(g,p),g.index=0,g.sibling=null,g}function l(g,p,v){return g.index=v,e?(v=g.alternate,v!==null?(v=v.index,v<p?(g.flags|=2,p):v):(g.flags|=2,p)):(g.flags|=1048576,p)}function a(g){return e&&g.alternate===null&&(g.flags|=2),g}function u(g,p,v,_){return p===null||p.tag!==6?(p=fa(v,g.mode,_),p.return=g,p):(p=i(p,v),p.return=g,p)}function d(g,p,v,_){var V=v.type;return V===ke?j(g,p,v.props.children,_,v.key):p!==null&&(p.elementType===V||typeof V=="object"&&V!==null&&V.$$typeof===se&&Ds(V)===p.type)?(_=i(p,v.props),_.ref=Yr(g,p,v),_.return=g,_):(_=Sl(v.type,v.key,v.props,null,g.mode,_),_.ref=Yr(g,p,v),_.return=g,_)}function y(g,p,v,_){return p===null||p.tag!==4||p.stateNode.containerInfo!==v.containerInfo||p.stateNode.implementation!==v.implementation?(p=pa(v,g.mode,_),p.return=g,p):(p=i(p,v.children||[]),p.return=g,p)}function j(g,p,v,_,V){return p===null||p.tag!==7?(p=Gn(v,g.mode,_,V),p.return=g,p):(p=i(p,v),p.return=g,p)}function C(g,p,v){if(typeof p=="string"&&p!==""||typeof p=="number")return p=fa(""+p,g.mode,v),p.return=g,p;if(typeof p=="object"&&p!==null){switch(p.$$typeof){case Me:return v=Sl(p.type,p.key,p.props,null,g.mode,v),v.ref=Yr(g,null,p),v.return=g,v;case fe:return p=pa(p,g.mode,v),p.return=g,p;case se:var _=p._init;return C(g,_(p._payload),v)}if(Dt(p)||B(p))return p=Gn(p,g.mode,v,null),p.return=g,p;Zi(g,p)}return null}function S(g,p,v,_){var V=p!==null?p.key:null;if(typeof v=="string"&&v!==""||typeof v=="number")return V!==null?null:u(g,p,""+v,_);if(typeof v=="object"&&v!==null){switch(v.$$typeof){case Me:return v.key===V?d(g,p,v,_):null;case fe:return v.key===V?y(g,p,v,_):null;case se:return V=v._init,S(g,p,V(v._payload),_)}if(Dt(v)||B(v))return V!==null?null:j(g,p,v,_,null);Zi(g,v)}return null}function M(g,p,v,_,V){if(typeof _=="string"&&_!==""||typeof _=="number")return g=g.get(v)||null,u(p,g,""+_,V);if(typeof _=="object"&&_!==null){switch(_.$$typeof){case Me:return g=g.get(_.key===null?v:_.key)||null,d(p,g,_,V);case fe:return g=g.get(_.key===null?v:_.key)||null,y(p,g,_,V);case se:var W=_._init;return M(g,p,v,W(_._payload),V)}if(Dt(_)||B(_))return g=g.get(v)||null,j(p,g,_,V,null);Zi(p,_)}return null}function I(g,p,v,_){for(var V=null,W=null,Q=p,Y=p=0,We=null;Q!==null&&Y<v.length;Y++){Q.index>Y?(We=Q,Q=null):We=Q.sibling;var me=S(g,Q,v[Y],_);if(me===null){Q===null&&(Q=We);break}e&&Q&&me.alternate===null&&t(g,Q),p=l(me,p,Y),W===null?V=me:W.sibling=me,W=me,Q=We}if(Y===v.length)return n(g,Q),Pe&&Vn(g,Y),V;if(Q===null){for(;Y<v.length;Y++)Q=C(g,v[Y],_),Q!==null&&(p=l(Q,p,Y),W===null?V=Q:W.sibling=Q,W=Q);return Pe&&Vn(g,Y),V}for(Q=r(g,Q);Y<v.length;Y++)We=M(Q,g,Y,v[Y],_),We!==null&&(e&&We.alternate!==null&&Q.delete(We.key===null?Y:We.key),p=l(We,p,Y),W===null?V=We:W.sibling=We,W=We);return e&&Q.forEach(function(Pn){return t(g,Pn)}),Pe&&Vn(g,Y),V}function A(g,p,v,_){var V=B(v);if(typeof V!="function")throw Error(f(150));if(v=V.call(v),v==null)throw Error(f(151));for(var W=V=null,Q=p,Y=p=0,We=null,me=v.next();Q!==null&&!me.done;Y++,me=v.next()){Q.index>Y?(We=Q,Q=null):We=Q.sibling;var Pn=S(g,Q,me.value,_);if(Pn===null){Q===null&&(Q=We);break}e&&Q&&Pn.alternate===null&&t(g,Q),p=l(Pn,p,Y),W===null?V=Pn:W.sibling=Pn,W=Pn,Q=We}if(me.done)return n(g,Q),Pe&&Vn(g,Y),V;if(Q===null){for(;!me.done;Y++,me=v.next())me=C(g,me.value,_),me!==null&&(p=l(me,p,Y),W===null?V=me:W.sibling=me,W=me);return Pe&&Vn(g,Y),V}for(Q=r(g,Q);!me.done;Y++,me=v.next())me=M(Q,g,Y,me.value,_),me!==null&&(e&&me.alternate!==null&&Q.delete(me.key===null?Y:me.key),p=l(me,p,Y),W===null?V=me:W.sibling=me,W=me);return e&&Q.forEach(function(nf){return t(g,nf)}),Pe&&Vn(g,Y),V}function Re(g,p,v,_){if(typeof v=="object"&&v!==null&&v.type===ke&&v.key===null&&(v=v.props.children),typeof v=="object"&&v!==null){switch(v.$$typeof){case Me:e:{for(var V=v.key,W=p;W!==null;){if(W.key===V){if(V=v.type,V===ke){if(W.tag===7){n(g,W.sibling),p=i(W,v.props.children),p.return=g,g=p;break e}}else if(W.elementType===V||typeof V=="object"&&V!==null&&V.$$typeof===se&&Ds(V)===W.type){n(g,W.sibling),p=i(W,v.props),p.ref=Yr(g,W,v),p.return=g,g=p;break e}n(g,W);break}else t(g,W);W=W.sibling}v.type===ke?(p=Gn(v.props.children,g.mode,_,v.key),p.return=g,g=p):(_=Sl(v.type,v.key,v.props,null,g.mode,_),_.ref=Yr(g,p,v),_.return=g,g=_)}return a(g);case fe:e:{for(W=v.key;p!==null;){if(p.key===W)if(p.tag===4&&p.stateNode.containerInfo===v.containerInfo&&p.stateNode.implementation===v.implementation){n(g,p.sibling),p=i(p,v.children||[]),p.return=g,g=p;break e}else{n(g,p);break}else t(g,p);p=p.sibling}p=pa(v,g.mode,_),p.return=g,g=p}return a(g);case se:return W=v._init,Re(g,p,W(v._payload),_)}if(Dt(v))return I(g,p,v,_);if(B(v))return A(g,p,v,_);Zi(g,v)}return typeof v=="string"&&v!==""||typeof v=="number"?(v=""+v,p!==null&&p.tag===6?(n(g,p.sibling),p=i(p,v),p.return=g,g=p):(n(g,p),p=fa(v,g.mode,_),p.return=g,g=p),a(g)):n(g,p)}return Re}var mr=Ms(!0),Ts=Ms(!1),Ji=yn(null),el=null,hr=null,So=null;function jo(){So=hr=el=null}function No(e){var t=Ji.current;_e(Ji),e._currentValue=t}function Co(e,t,n){for(;e!==null;){var r=e.alternate;if((e.childLanes&t)!==t?(e.childLanes|=t,r!==null&&(r.childLanes|=t)):r!==null&&(r.childLanes&t)!==t&&(r.childLanes|=t),e===n)break;e=e.return}}function gr(e,t){el=e,So=hr=null,e=e.dependencies,e!==null&&e.firstContext!==null&&((e.lanes&t)!==0&&(st=!0),e.firstContext=null)}function Ct(e){var t=e._currentValue;if(So!==e)if(e={context:e,memoizedValue:t,next:null},hr===null){if(el===null)throw Error(f(308));hr=e,el.dependencies={lanes:0,firstContext:e}}else hr=hr.next=e;return t}var bn=null;function zo(e){bn===null?bn=[e]:bn.push(e)}function Fs(e,t,n,r){var i=t.interleaved;return i===null?(n.next=n,zo(t)):(n.next=i.next,i.next=n),t.interleaved=n,nn(e,r)}function nn(e,t){e.lanes|=t;var n=e.alternate;for(n!==null&&(n.lanes|=t),n=e,e=e.return;e!==null;)e.childLanes|=t,n=e.alternate,n!==null&&(n.childLanes|=t),n=e,e=e.return;return n.tag===3?n.stateNode:null}var kn=!1;function Eo(e){e.updateQueue={baseState:e.memoizedState,firstBaseUpdate:null,lastBaseUpdate:null,shared:{pending:null,interleaved:null,lanes:0},effects:null}}function Rs(e,t){e=e.updateQueue,t.updateQueue===e&&(t.updateQueue={baseState:e.baseState,firstBaseUpdate:e.firstBaseUpdate,lastBaseUpdate:e.lastBaseUpdate,shared:e.shared,effects:e.effects})}function rn(e,t){return{eventTime:e,lane:t,tag:0,payload:null,callback:null,next:null}}function Sn(e,t,n){var r=e.updateQueue;if(r===null)return null;if(r=r.shared,(ce&2)!==0){var i=r.pending;return i===null?t.next=t:(t.next=i.next,i.next=t),r.pending=t,nn(e,n)}return i=r.interleaved,i===null?(t.next=t,zo(r)):(t.next=i.next,i.next=t),r.interleaved=t,nn(e,n)}function tl(e,t,n){if(t=t.updateQueue,t!==null&&(t=t.shared,(n&4194240)!==0)){var r=t.lanes;r&=e.pendingLanes,n|=r,t.lanes=n,Bl(e,n)}}function Is(e,t){var n=e.updateQueue,r=e.alternate;if(r!==null&&(r=r.updateQueue,n===r)){var i=null,l=null;if(n=n.firstBaseUpdate,n!==null){do{var a={eventTime:n.eventTime,lane:n.lane,tag:n.tag,payload:n.payload,callback:n.callback,next:null};l===null?i=l=a:l=l.next=a,n=n.next}while(n!==null);l===null?i=l=t:l=l.next=t}else i=l=t;n={baseState:r.baseState,firstBaseUpdate:i,lastBaseUpdate:l,shared:r.shared,effects:r.effects},e.updateQueue=n;return}e=n.lastBaseUpdate,e===null?n.firstBaseUpdate=t:e.next=t,n.lastBaseUpdate=t}function nl(e,t,n,r){var i=e.updateQueue;kn=!1;var l=i.firstBaseUpdate,a=i.lastBaseUpdate,u=i.shared.pending;if(u!==null){i.shared.pending=null;var d=u,y=d.next;d.next=null,a===null?l=y:a.next=y,a=d;var j=e.alternate;j!==null&&(j=j.updateQueue,u=j.lastBaseUpdate,u!==a&&(u===null?j.firstBaseUpdate=y:u.next=y,j.lastBaseUpdate=d))}if(l!==null){var C=i.baseState;a=0,j=y=d=null,u=l;do{var S=u.lane,M=u.eventTime;if((r&S)===S){j!==null&&(j=j.next={eventTime:M,lane:0,tag:u.tag,payload:u.payload,callback:u.callback,next:null});e:{var I=e,A=u;switch(S=t,M=n,A.tag){case 1:if(I=A.payload,typeof I=="function"){C=I.call(M,C,S);break e}C=I;break e;case 3:I.flags=I.flags&-65537|128;case 0:if(I=A.payload,S=typeof I=="function"?I.call(M,C,S):I,S==null)break e;C=F({},C,S);break e;case 2:kn=!0}}u.callback!==null&&u.lane!==0&&(e.flags|=64,S=i.effects,S===null?i.effects=[u]:S.push(u))}else M={eventTime:M,lane:S,tag:u.tag,payload:u.payload,callback:u.callback,next:null},j===null?(y=j=M,d=C):j=j.next=M,a|=S;if(u=u.next,u===null){if(u=i.shared.pending,u===null)break;S=u,u=S.next,S.next=null,i.lastBaseUpdate=S,i.shared.pending=null}}while(!0);if(j===null&&(d=C),i.baseState=d,i.firstBaseUpdate=y,i.lastBaseUpdate=j,t=i.shared.interleaved,t!==null){i=t;do a|=i.lane,i=i.next;while(i!==t)}else l===null&&(i.shared.lanes=0);$n|=a,e.lanes=a,e.memoizedState=C}}function Os(e,t,n){if(e=t.effects,t.effects=null,e!==null)for(t=0;t<e.length;t++){var r=e[t],i=r.callback;if(i!==null){if(r.callback=null,r=n,typeof i!="function")throw Error(f(191,i));i.call(r)}}}var Gr={},Qt=yn(Gr),qr=yn(Gr),Xr=yn(Gr);function Wn(e){if(e===Gr)throw Error(f(174));return e}function _o(e,t){switch(Ce(Xr,t),Ce(qr,e),Ce(Qt,Gr),e=t.nodeType,e){case 9:case 11:t=(t=t.documentElement)?t.namespaceURI:Dn(null,"");break;default:e=e===8?t.parentNode:t,t=e.namespaceURI||null,e=e.tagName,t=Dn(t,e)}_e(Qt),Ce(Qt,t)}function vr(){_e(Qt),_e(qr),_e(Xr)}function As(e){Wn(Xr.current);var t=Wn(Qt.current),n=Dn(t,e.type);t!==n&&(Ce(qr,e),Ce(Qt,n))}function Po(e){qr.current===e&&(_e(Qt),_e(qr))}var Le=yn(0);function rl(e){for(var t=e;t!==null;){if(t.tag===13){var n=t.memoizedState;if(n!==null&&(n=n.dehydrated,n===null||n.data==="$?"||n.data==="$!"))return t}else if(t.tag===19&&t.memoizedProps.revealOrder!==void 0){if((t.flags&128)!==0)return t}else if(t.child!==null){t.child.return=t,t=t.child;continue}if(t===e)break;for(;t.sibling===null;){if(t.return===null||t.return===e)return null;t=t.return}t.sibling.return=t.return,t=t.sibling}return null}var Lo=[];function Do(){for(var e=0;e<Lo.length;e++)Lo[e]._workInProgressVersionPrimary=null;Lo.length=0}var il=de.ReactCurrentDispatcher,Mo=de.ReactCurrentBatchConfig,Qn=0,De=null,Oe=null,Ve=null,ll=!1,Zr=!1,Jr=0,Nd=0;function Ze(){throw Error(f(321))}function To(e,t){if(t===null)return!1;for(var n=0;n<t.length&&n<e.length;n++)if(!Tt(e[n],t[n]))return!1;return!0}function Fo(e,t,n,r,i,l){if(Qn=l,De=t,t.memoizedState=null,t.updateQueue=null,t.lanes=0,il.current=e===null||e.memoizedState===null?_d:Pd,e=n(r,i),Zr){l=0;do{if(Zr=!1,Jr=0,25<=l)throw Error(f(301));l+=1,Ve=Oe=null,t.updateQueue=null,il.current=Ld,e=n(r,i)}while(Zr)}if(il.current=sl,t=Oe!==null&&Oe.next!==null,Qn=0,Ve=Oe=De=null,ll=!1,t)throw Error(f(300));return e}function Ro(){var e=Jr!==0;return Jr=0,e}function $t(){var e={memoizedState:null,baseState:null,baseQueue:null,queue:null,next:null};return Ve===null?De.memoizedState=Ve=e:Ve=Ve.next=e,Ve}function zt(){if(Oe===null){var e=De.alternate;e=e!==null?e.memoizedState:null}else e=Oe.next;var t=Ve===null?De.memoizedState:Ve.next;if(t!==null)Ve=t,Oe=e;else{if(e===null)throw Error(f(310));Oe=e,e={memoizedState:Oe.memoizedState,baseState:Oe.baseState,baseQueue:Oe.baseQueue,queue:Oe.queue,next:null},Ve===null?De.memoizedState=Ve=e:Ve=Ve.next=e}return Ve}function ei(e,t){return typeof t=="function"?t(e):t}function Io(e){var t=zt(),n=t.queue;if(n===null)throw Error(f(311));n.lastRenderedReducer=e;var r=Oe,i=r.baseQueue,l=n.pending;if(l!==null){if(i!==null){var a=i.next;i.next=l.next,l.next=a}r.baseQueue=i=l,n.pending=null}if(i!==null){l=i.next,r=r.baseState;var u=a=null,d=null,y=l;do{var j=y.lane;if((Qn&j)===j)d!==null&&(d=d.next={lane:0,action:y.action,hasEagerState:y.hasEagerState,eagerState:y.eagerState,next:null}),r=y.hasEagerState?y.eagerState:e(r,y.action);else{var C={lane:j,action:y.action,hasEagerState:y.hasEagerState,eagerState:y.eagerState,next:null};d===null?(u=d=C,a=r):d=d.next=C,De.lanes|=j,$n|=j}y=y.next}while(y!==null&&y!==l);d===null?a=r:d.next=u,Tt(r,t.memoizedState)||(st=!0),t.memoizedState=r,t.baseState=a,t.baseQueue=d,n.lastRenderedState=r}if(e=n.interleaved,e!==null){i=e;do l=i.lane,De.lanes|=l,$n|=l,i=i.next;while(i!==e)}else i===null&&(n.lanes=0);return[t.memoizedState,n.dispatch]}function Oo(e){var t=zt(),n=t.queue;if(n===null)throw Error(f(311));n.lastRenderedReducer=e;var r=n.dispatch,i=n.pending,l=t.memoizedState;if(i!==null){n.pending=null;var a=i=i.next;do l=e(l,a.action),a=a.next;while(a!==i);Tt(l,t.memoizedState)||(st=!0),t.memoizedState=l,t.baseQueue===null&&(t.baseState=l),n.lastRenderedState=l}return[l,r]}function Us(){}function Bs(e,t){var n=De,r=zt(),i=t(),l=!Tt(r.memoizedState,i);if(l&&(r.memoizedState=i,st=!0),r=r.queue,Ao(Ws.bind(null,n,r,e),[e]),r.getSnapshot!==t||l||Ve!==null&&Ve.memoizedState.tag&1){if(n.flags|=2048,ti(9,bs.bind(null,n,r,i,t),void 0,null),be===null)throw Error(f(349));(Qn&30)!==0||Vs(n,t,i)}return i}function Vs(e,t,n){e.flags|=16384,e={getSnapshot:t,value:n},t=De.updateQueue,t===null?(t={lastEffect:null,stores:null},De.updateQueue=t,t.stores=[e]):(n=t.stores,n===null?t.stores=[e]:n.push(e))}function bs(e,t,n,r){t.value=n,t.getSnapshot=r,Qs(t)&&$s(e)}function Ws(e,t,n){return n(function(){Qs(t)&&$s(e)})}function Qs(e){var t=e.getSnapshot;e=e.value;try{var n=t();return!Tt(e,n)}catch{return!0}}function $s(e){var t=nn(e,1);t!==null&&At(t,e,1,-1)}function Hs(e){var t=$t();return typeof e=="function"&&(e=e()),t.memoizedState=t.baseState=e,e={pending:null,interleaved:null,lanes:0,dispatch:null,lastRenderedReducer:ei,lastRenderedState:e},t.queue=e,e=e.dispatch=Ed.bind(null,De,e),[t.memoizedState,e]}function ti(e,t,n,r){return e={tag:e,create:t,destroy:n,deps:r,next:null},t=De.updateQueue,t===null?(t={lastEffect:null,stores:null},De.updateQueue=t,t.lastEffect=e.next=e):(n=t.lastEffect,n===null?t.lastEffect=e.next=e:(r=n.next,n.next=e,e.next=r,t.lastEffect=e)),e}function Ks(){return zt().memoizedState}function ol(e,t,n,r){var i=$t();De.flags|=e,i.memoizedState=ti(1|t,n,void 0,r===void 0?null:r)}function al(e,t,n,r){var i=zt();r=r===void 0?null:r;var l=void 0;if(Oe!==null){var a=Oe.memoizedState;if(l=a.destroy,r!==null&&To(r,a.deps)){i.memoizedState=ti(t,n,l,r);return}}De.flags|=e,i.memoizedState=ti(1|t,n,l,r)}function Ys(e,t){return ol(8390656,8,e,t)}function Ao(e,t){return al(2048,8,e,t)}function Gs(e,t){return al(4,2,e,t)}function qs(e,t){return al(4,4,e,t)}function Xs(e,t){if(typeof t=="function")return e=e(),t(e),function(){t(null)};if(t!=null)return e=e(),t.current=e,function(){t.current=null}}function Zs(e,t,n){return n=n!=null?n.concat([e]):null,al(4,4,Xs.bind(null,t,e),n)}function Uo(){}function Js(e,t){var n=zt();t=t===void 0?null:t;var r=n.memoizedState;return r!==null&&t!==null&&To(t,r[1])?r[0]:(n.memoizedState=[e,t],e)}function eu(e,t){var n=zt();t=t===void 0?null:t;var r=n.memoizedState;return r!==null&&t!==null&&To(t,r[1])?r[0]:(e=e(),n.memoizedState=[e,t],e)}function tu(e,t,n){return(Qn&21)===0?(e.baseState&&(e.baseState=!1,st=!0),e.memoizedState=n):(Tt(n,t)||(n=Da(),De.lanes|=n,$n|=n,e.baseState=!0),t)}function Cd(e,t){var n=ge;ge=n!==0&&4>n?n:4,e(!0);var r=Mo.transition;Mo.transition={};try{e(!1),t()}finally{ge=n,Mo.transition=r}}function nu(){return zt().memoizedState}function zd(e,t,n){var r=zn(e);if(n={lane:r,action:n,hasEagerState:!1,eagerState:null,next:null},ru(e))iu(t,n);else if(n=Fs(e,t,n,r),n!==null){var i=rt();At(n,e,r,i),lu(n,t,r)}}function Ed(e,t,n){var r=zn(e),i={lane:r,action:n,hasEagerState:!1,eagerState:null,next:null};if(ru(e))iu(t,i);else{var l=e.alternate;if(e.lanes===0&&(l===null||l.lanes===0)&&(l=t.lastRenderedReducer,l!==null))try{var a=t.lastRenderedState,u=l(a,n);if(i.hasEagerState=!0,i.eagerState=u,Tt(u,a)){var d=t.interleaved;d===null?(i.next=i,zo(t)):(i.next=d.next,d.next=i),t.interleaved=i;return}}catch{}finally{}n=Fs(e,t,i,r),n!==null&&(i=rt(),At(n,e,r,i),lu(n,t,r))}}function ru(e){var t=e.alternate;return e===De||t!==null&&t===De}function iu(e,t){Zr=ll=!0;var n=e.pending;n===null?t.next=t:(t.next=n.next,n.next=t),e.pending=t}function lu(e,t,n){if((n&4194240)!==0){var r=t.lanes;r&=e.pendingLanes,n|=r,t.lanes=n,Bl(e,n)}}var sl={readContext:Ct,useCallback:Ze,useContext:Ze,useEffect:Ze,useImperativeHandle:Ze,useInsertionEffect:Ze,useLayoutEffect:Ze,useMemo:Ze,useReducer:Ze,useRef:Ze,useState:Ze,useDebugValue:Ze,useDeferredValue:Ze,useTransition:Ze,useMutableSource:Ze,useSyncExternalStore:Ze,useId:Ze,unstable_isNewReconciler:!1},_d={readContext:Ct,useCallback:function(e,t){return $t().memoizedState=[e,t===void 0?null:t],e},useContext:Ct,useEffect:Ys,useImperativeHandle:function(e,t,n){return n=n!=null?n.concat([e]):null,ol(4194308,4,Xs.bind(null,t,e),n)},useLayoutEffect:function(e,t){return ol(4194308,4,e,t)},useInsertionEffect:function(e,t){return ol(4,2,e,t)},useMemo:function(e,t){var n=$t();return t=t===void 0?null:t,e=e(),n.memoizedState=[e,t],e},useReducer:function(e,t,n){var r=$t();return t=n!==void 0?n(t):t,r.memoizedState=r.baseState=t,e={pending:null,interleaved:null,lanes:0,dispatch:null,lastRenderedReducer:e,lastRenderedState:t},r.queue=e,e=e.dispatch=zd.bind(null,De,e),[r.memoizedState,e]},useRef:function(e){var t=$t();return e={current:e},t.memoizedState=e},useState:Hs,useDebugValue:Uo,useDeferredValue:function(e){return $t().memoizedState=e},useTransition:function(){var e=Hs(!1),t=e[0];return e=Cd.bind(null,e[1]),$t().memoizedState=e,[t,e]},useMutableSource:function(){},useSyncExternalStore:function(e,t,n){var r=De,i=$t();if(Pe){if(n===void 0)throw Error(f(407));n=n()}else{if(n=t(),be===null)throw Error(f(349));(Qn&30)!==0||Vs(r,t,n)}i.memoizedState=n;var l={value:n,getSnapshot:t};return i.queue=l,Ys(Ws.bind(null,r,l,e),[e]),r.flags|=2048,ti(9,bs.bind(null,r,l,n,t),void 0,null),n},useId:function(){var e=$t(),t=be.identifierPrefix;if(Pe){var n=tn,r=en;n=(r&~(1<<32-Mt(r)-1)).toString(32)+n,t=":"+t+"R"+n,n=Jr++,0<n&&(t+="H"+n.toString(32)),t+=":"}else n=Nd++,t=":"+t+"r"+n.toString(32)+":";return e.memoizedState=t},unstable_isNewReconciler:!1},Pd={readContext:Ct,useCallback:Js,useContext:Ct,useEffect:Ao,useImperativeHandle:Zs,useInsertionEffect:Gs,useLayoutEffect:qs,useMemo:eu,useReducer:Io,useRef:Ks,useState:function(){return Io(ei)},useDebugValue:Uo,useDeferredValue:function(e){var t=zt();return tu(t,Oe.memoizedState,e)},useTransition:function(){var e=Io(ei)[0],t=zt().memoizedState;return[e,t]},useMutableSource:Us,useSyncExternalStore:Bs,useId:nu,unstable_isNewReconciler:!1},Ld={readContext:Ct,useCallback:Js,useContext:Ct,useEffect:Ao,useImperativeHandle:Zs,useInsertionEffect:Gs,useLayoutEffect:qs,useMemo:eu,useReducer:Oo,useRef:Ks,useState:function(){return Oo(ei)},useDebugValue:Uo,useDeferredValue:function(e){var t=zt();return Oe===null?t.memoizedState=e:tu(t,Oe.memoizedState,e)},useTransition:function(){var e=Oo(ei)[0],t=zt().memoizedState;return[e,t]},useMutableSource:Us,useSyncExternalStore:Bs,useId:nu,unstable_isNewReconciler:!1};function Rt(e,t){if(e&&e.defaultProps){t=F({},t),e=e.defaultProps;for(var n in e)t[n]===void 0&&(t[n]=e[n]);return t}return t}function Bo(e,t,n,r){t=e.memoizedState,n=n(r,t),n=n==null?t:F({},t,n),e.memoizedState=n,e.lanes===0&&(e.updateQueue.baseState=n)}var ul={isMounted:function(e){return(e=e._reactInternals)?Vt(e)===e:!1},enqueueSetState:function(e,t,n){e=e._reactInternals;var r=rt(),i=zn(e),l=rn(r,i);l.payload=t,n!=null&&(l.callback=n),t=Sn(e,l,i),t!==null&&(At(t,e,i,r),tl(t,e,i))},enqueueReplaceState:function(e,t,n){e=e._reactInternals;var r=rt(),i=zn(e),l=rn(r,i);l.tag=1,l.payload=t,n!=null&&(l.callback=n),t=Sn(e,l,i),t!==null&&(At(t,e,i,r),tl(t,e,i))},enqueueForceUpdate:function(e,t){e=e._reactInternals;var n=rt(),r=zn(e),i=rn(n,r);i.tag=2,t!=null&&(i.callback=t),t=Sn(e,i,r),t!==null&&(At(t,e,r,n),tl(t,e,r))}};function ou(e,t,n,r,i,l,a){return e=e.stateNode,typeof e.shouldComponentUpdate=="function"?e.shouldComponentUpdate(r,l,a):t.prototype&&t.prototype.isPureReactComponent?!Vr(n,r)||!Vr(i,l):!0}function au(e,t,n){var r=!1,i=xn,l=t.contextType;return typeof l=="object"&&l!==null?l=Ct(l):(i=at(t)?Un:Xe.current,r=t.contextTypes,l=(r=r!=null)?cr(e,i):xn),t=new t(n,l),e.memoizedState=t.state!==null&&t.state!==void 0?t.state:null,t.updater=ul,e.stateNode=t,t._reactInternals=e,r&&(e=e.stateNode,e.__reactInternalMemoizedUnmaskedChildContext=i,e.__reactInternalMemoizedMaskedChildContext=l),t}function su(e,t,n,r){e=t.state,typeof t.componentWillReceiveProps=="function"&&t.componentWillReceiveProps(n,r),typeof t.UNSAFE_componentWillReceiveProps=="function"&&t.UNSAFE_componentWillReceiveProps(n,r),t.state!==e&&ul.enqueueReplaceState(t,t.state,null)}function Vo(e,t,n,r){var i=e.stateNode;i.props=n,i.state=e.memoizedState,i.refs={},Eo(e);var l=t.contextType;typeof l=="object"&&l!==null?i.context=Ct(l):(l=at(t)?Un:Xe.current,i.context=cr(e,l)),i.state=e.memoizedState,l=t.getDerivedStateFromProps,typeof l=="function"&&(Bo(e,t,l,n),i.state=e.memoizedState),typeof t.getDerivedStateFromProps=="function"||typeof i.getSnapshotBeforeUpdate=="function"||typeof i.UNSAFE_componentWillMount!="function"&&typeof i.componentWillMount!="function"||(t=i.state,typeof i.componentWillMount=="function"&&i.componentWillMount(),typeof i.UNSAFE_componentWillMount=="function"&&i.UNSAFE_componentWillMount(),t!==i.state&&ul.enqueueReplaceState(i,i.state,null),nl(e,n,i,r),i.state=e.memoizedState),typeof i.componentDidMount=="function"&&(e.flags|=4194308)}function yr(e,t){try{var n="",r=t;do n+=ie(r),r=r.return;while(r);var i=n}catch(l){i=`
Error generating stack: `+l.message+`
`+l.stack}return{value:e,source:t,stack:i,digest:null}}function bo(e,t,n){return{value:e,source:null,stack:n??null,digest:t??null}}function Wo(e,t){try{console.error(t.value)}catch(n){setTimeout(function(){throw n})}}var Dd=typeof WeakMap=="function"?WeakMap:Map;function uu(e,t,n){n=rn(-1,n),n.tag=3,n.payload={element:null};var r=t.value;return n.callback=function(){gl||(gl=!0,ia=r),Wo(e,t)},n}function cu(e,t,n){n=rn(-1,n),n.tag=3;var r=e.type.getDerivedStateFromError;if(typeof r=="function"){var i=t.value;n.payload=function(){return r(i)},n.callback=function(){Wo(e,t)}}var l=e.stateNode;return l!==null&&typeof l.componentDidCatch=="function"&&(n.callback=function(){Wo(e,t),typeof r!="function"&&(Nn===null?Nn=new Set([this]):Nn.add(this));var a=t.stack;this.componentDidCatch(t.value,{componentStack:a!==null?a:""})}),n}function du(e,t,n){var r=e.pingCache;if(r===null){r=e.pingCache=new Dd;var i=new Set;r.set(t,i)}else i=r.get(t),i===void 0&&(i=new Set,r.set(t,i));i.has(n)||(i.add(n),e=$d.bind(null,e,t,n),t.then(e,e))}function fu(e){do{var t;if((t=e.tag===13)&&(t=e.memoizedState,t=t!==null?t.dehydrated!==null:!0),t)return e;e=e.return}while(e!==null);return null}function pu(e,t,n,r,i){return(e.mode&1)===0?(e===t?e.flags|=65536:(e.flags|=128,n.flags|=131072,n.flags&=-52805,n.tag===1&&(n.alternate===null?n.tag=17:(t=rn(-1,1),t.tag=2,Sn(n,t,1))),n.lanes|=1),e):(e.flags|=65536,e.lanes=i,e)}var Md=de.ReactCurrentOwner,st=!1;function nt(e,t,n,r){t.child=e===null?Ts(t,null,n,r):mr(t,e.child,n,r)}function mu(e,t,n,r,i){n=n.render;var l=t.ref;return gr(t,i),r=Fo(e,t,n,r,l,i),n=Ro(),e!==null&&!st?(t.updateQueue=e.updateQueue,t.flags&=-2053,e.lanes&=~i,ln(e,t,i)):(Pe&&n&&vo(t),t.flags|=1,nt(e,t,r,i),t.child)}function hu(e,t,n,r,i){if(e===null){var l=n.type;return typeof l=="function"&&!da(l)&&l.defaultProps===void 0&&n.compare===null&&n.defaultProps===void 0?(t.tag=15,t.type=l,gu(e,t,l,r,i)):(e=Sl(n.type,null,r,t,t.mode,i),e.ref=t.ref,e.return=t,t.child=e)}if(l=e.child,(e.lanes&i)===0){var a=l.memoizedProps;if(n=n.compare,n=n!==null?n:Vr,n(a,r)&&e.ref===t.ref)return ln(e,t,i)}return t.flags|=1,e=_n(l,r),e.ref=t.ref,e.return=t,t.child=e}function gu(e,t,n,r,i){if(e!==null){var l=e.memoizedProps;if(Vr(l,r)&&e.ref===t.ref)if(st=!1,t.pendingProps=r=l,(e.lanes&i)!==0)(e.flags&131072)!==0&&(st=!0);else return t.lanes=e.lanes,ln(e,t,i)}return Qo(e,t,n,r,i)}function vu(e,t,n){var r=t.pendingProps,i=r.children,l=e!==null?e.memoizedState:null;if(r.mode==="hidden")if((t.mode&1)===0)t.memoizedState={baseLanes:0,cachePool:null,transitions:null},Ce(wr,vt),vt|=n;else{if((n&1073741824)===0)return e=l!==null?l.baseLanes|n:n,t.lanes=t.childLanes=1073741824,t.memoizedState={baseLanes:e,cachePool:null,transitions:null},t.updateQueue=null,Ce(wr,vt),vt|=e,null;t.memoizedState={baseLanes:0,cachePool:null,transitions:null},r=l!==null?l.baseLanes:n,Ce(wr,vt),vt|=r}else l!==null?(r=l.baseLanes|n,t.memoizedState=null):r=n,Ce(wr,vt),vt|=r;return nt(e,t,i,n),t.child}function yu(e,t){var n=t.ref;(e===null&&n!==null||e!==null&&e.ref!==n)&&(t.flags|=512,t.flags|=2097152)}function Qo(e,t,n,r,i){var l=at(n)?Un:Xe.current;return l=cr(t,l),gr(t,i),n=Fo(e,t,n,r,l,i),r=Ro(),e!==null&&!st?(t.updateQueue=e.updateQueue,t.flags&=-2053,e.lanes&=~i,ln(e,t,i)):(Pe&&r&&vo(t),t.flags|=1,nt(e,t,n,i),t.child)}function xu(e,t,n,r,i){if(at(n)){var l=!0;Ki(t)}else l=!1;if(gr(t,i),t.stateNode===null)dl(e,t),au(t,n,r),Vo(t,n,r,i),r=!0;else if(e===null){var a=t.stateNode,u=t.memoizedProps;a.props=u;var d=a.context,y=n.contextType;typeof y=="object"&&y!==null?y=Ct(y):(y=at(n)?Un:Xe.current,y=cr(t,y));var j=n.getDerivedStateFromProps,C=typeof j=="function"||typeof a.getSnapshotBeforeUpdate=="function";C||typeof a.UNSAFE_componentWillReceiveProps!="function"&&typeof a.componentWillReceiveProps!="function"||(u!==r||d!==y)&&su(t,a,r,y),kn=!1;var S=t.memoizedState;a.state=S,nl(t,r,a,i),d=t.memoizedState,u!==r||S!==d||ot.current||kn?(typeof j=="function"&&(Bo(t,n,j,r),d=t.memoizedState),(u=kn||ou(t,n,u,r,S,d,y))?(C||typeof a.UNSAFE_componentWillMount!="function"&&typeof a.componentWillMount!="function"||(typeof a.componentWillMount=="function"&&a.componentWillMount(),typeof a.UNSAFE_componentWillMount=="function"&&a.UNSAFE_componentWillMount()),typeof a.componentDidMount=="function"&&(t.flags|=4194308)):(typeof a.componentDidMount=="function"&&(t.flags|=4194308),t.memoizedProps=r,t.memoizedState=d),a.props=r,a.state=d,a.context=y,r=u):(typeof a.componentDidMount=="function"&&(t.flags|=4194308),r=!1)}else{a=t.stateNode,Rs(e,t),u=t.memoizedProps,y=t.type===t.elementType?u:Rt(t.type,u),a.props=y,C=t.pendingProps,S=a.context,d=n.contextType,typeof d=="object"&&d!==null?d=Ct(d):(d=at(n)?Un:Xe.current,d=cr(t,d));var M=n.getDerivedStateFromProps;(j=typeof M=="function"||typeof a.getSnapshotBeforeUpdate=="function")||typeof a.UNSAFE_componentWillReceiveProps!="function"&&typeof a.componentWillReceiveProps!="function"||(u!==C||S!==d)&&su(t,a,r,d),kn=!1,S=t.memoizedState,a.state=S,nl(t,r,a,i);var I=t.memoizedState;u!==C||S!==I||ot.current||kn?(typeof M=="function"&&(Bo(t,n,M,r),I=t.memoizedState),(y=kn||ou(t,n,y,r,S,I,d)||!1)?(j||typeof a.UNSAFE_componentWillUpdate!="function"&&typeof a.componentWillUpdate!="function"||(typeof a.componentWillUpdate=="function"&&a.componentWillUpdate(r,I,d),typeof a.UNSAFE_componentWillUpdate=="function"&&a.UNSAFE_componentWillUpdate(r,I,d)),typeof a.componentDidUpdate=="function"&&(t.flags|=4),typeof a.getSnapshotBeforeUpdate=="function"&&(t.flags|=1024)):(typeof a.componentDidUpdate!="function"||u===e.memoizedProps&&S===e.memoizedState||(t.flags|=4),typeof a.getSnapshotBeforeUpdate!="function"||u===e.memoizedProps&&S===e.memoizedState||(t.flags|=1024),t.memoizedProps=r,t.memoizedState=I),a.props=r,a.state=I,a.context=d,r=y):(typeof a.componentDidUpdate!="function"||u===e.memoizedProps&&S===e.memoizedState||(t.flags|=4),typeof a.getSnapshotBeforeUpdate!="function"||u===e.memoizedProps&&S===e.memoizedState||(t.flags|=1024),r=!1)}return $o(e,t,n,r,l,i)}function $o(e,t,n,r,i,l){yu(e,t);var a=(t.flags&128)!==0;if(!r&&!a)return i&&Ns(t,n,!1),ln(e,t,l);r=t.stateNode,Md.current=t;var u=a&&typeof n.getDerivedStateFromError!="function"?null:r.render();return t.flags|=1,e!==null&&a?(t.child=mr(t,e.child,null,l),t.child=mr(t,null,u,l)):nt(e,t,u,l),t.memoizedState=r.state,i&&Ns(t,n,!0),t.child}function wu(e){var t=e.stateNode;t.pendingContext?Ss(e,t.pendingContext,t.pendingContext!==t.context):t.context&&Ss(e,t.context,!1),_o(e,t.containerInfo)}function ku(e,t,n,r,i){return pr(),ko(i),t.flags|=256,nt(e,t,n,r),t.child}var Ho={dehydrated:null,treeContext:null,retryLane:0};function Ko(e){return{baseLanes:e,cachePool:null,transitions:null}}function Su(e,t,n){var r=t.pendingProps,i=Le.current,l=!1,a=(t.flags&128)!==0,u;if((u=a)||(u=e!==null&&e.memoizedState===null?!1:(i&2)!==0),u?(l=!0,t.flags&=-129):(e===null||e.memoizedState!==null)&&(i|=1),Ce(Le,i&1),e===null)return wo(t),e=t.memoizedState,e!==null&&(e=e.dehydrated,e!==null)?((t.mode&1)===0?t.lanes=1:e.data==="$!"?t.lanes=8:t.lanes=1073741824,null):(a=r.children,e=r.fallback,l?(r=t.mode,l=t.child,a={mode:"hidden",children:a},(r&1)===0&&l!==null?(l.childLanes=0,l.pendingProps=a):l=jl(a,r,0,null),e=Gn(e,r,n,null),l.return=t,e.return=t,l.sibling=e,t.child=l,t.child.memoizedState=Ko(n),t.memoizedState=Ho,e):Yo(t,a));if(i=e.memoizedState,i!==null&&(u=i.dehydrated,u!==null))return Td(e,t,a,r,u,i,n);if(l){l=r.fallback,a=t.mode,i=e.child,u=i.sibling;var d={mode:"hidden",children:r.children};return(a&1)===0&&t.child!==i?(r=t.child,r.childLanes=0,r.pendingProps=d,t.deletions=null):(r=_n(i,d),r.subtreeFlags=i.subtreeFlags&14680064),u!==null?l=_n(u,l):(l=Gn(l,a,n,null),l.flags|=2),l.return=t,r.return=t,r.sibling=l,t.child=r,r=l,l=t.child,a=e.child.memoizedState,a=a===null?Ko(n):{baseLanes:a.baseLanes|n,cachePool:null,transitions:a.transitions},l.memoizedState=a,l.childLanes=e.childLanes&~n,t.memoizedState=Ho,r}return l=e.child,e=l.sibling,r=_n(l,{mode:"visible",children:r.children}),(t.mode&1)===0&&(r.lanes=n),r.return=t,r.sibling=null,e!==null&&(n=t.deletions,n===null?(t.deletions=[e],t.flags|=16):n.push(e)),t.child=r,t.memoizedState=null,r}function Yo(e,t){return t=jl({mode:"visible",children:t},e.mode,0,null),t.return=e,e.child=t}function cl(e,t,n,r){return r!==null&&ko(r),mr(t,e.child,null,n),e=Yo(t,t.pendingProps.children),e.flags|=2,t.memoizedState=null,e}function Td(e,t,n,r,i,l,a){if(n)return t.flags&256?(t.flags&=-257,r=bo(Error(f(422))),cl(e,t,a,r)):t.memoizedState!==null?(t.child=e.child,t.flags|=128,null):(l=r.fallback,i=t.mode,r=jl({mode:"visible",children:r.children},i,0,null),l=Gn(l,i,a,null),l.flags|=2,r.return=t,l.return=t,r.sibling=l,t.child=r,(t.mode&1)!==0&&mr(t,e.child,null,a),t.child.memoizedState=Ko(a),t.memoizedState=Ho,l);if((t.mode&1)===0)return cl(e,t,a,null);if(i.data==="$!"){if(r=i.nextSibling&&i.nextSibling.dataset,r)var u=r.dgst;return r=u,l=Error(f(419)),r=bo(l,r,void 0),cl(e,t,a,r)}if(u=(a&e.childLanes)!==0,st||u){if(r=be,r!==null){switch(a&-a){case 4:i=2;break;case 16:i=8;break;case 64:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:case 4194304:case 8388608:case 16777216:case 33554432:case 67108864:i=32;break;case 536870912:i=268435456;break;default:i=0}i=(i&(r.suspendedLanes|a))!==0?0:i,i!==0&&i!==l.retryLane&&(l.retryLane=i,nn(e,i),At(r,e,i,-1))}return ca(),r=bo(Error(f(421))),cl(e,t,a,r)}return i.data==="$?"?(t.flags|=128,t.child=e.child,t=Hd.bind(null,e),i._reactRetry=t,null):(e=l.treeContext,gt=vn(i.nextSibling),ht=t,Pe=!0,Ft=null,e!==null&&(jt[Nt++]=en,jt[Nt++]=tn,jt[Nt++]=Bn,en=e.id,tn=e.overflow,Bn=t),t=Yo(t,r.children),t.flags|=4096,t)}function ju(e,t,n){e.lanes|=t;var r=e.alternate;r!==null&&(r.lanes|=t),Co(e.return,t,n)}function Go(e,t,n,r,i){var l=e.memoizedState;l===null?e.memoizedState={isBackwards:t,rendering:null,renderingStartTime:0,last:r,tail:n,tailMode:i}:(l.isBackwards=t,l.rendering=null,l.renderingStartTime=0,l.last=r,l.tail=n,l.tailMode=i)}function Nu(e,t,n){var r=t.pendingProps,i=r.revealOrder,l=r.tail;if(nt(e,t,r.children,n),r=Le.current,(r&2)!==0)r=r&1|2,t.flags|=128;else{if(e!==null&&(e.flags&128)!==0)e:for(e=t.child;e!==null;){if(e.tag===13)e.memoizedState!==null&&ju(e,n,t);else if(e.tag===19)ju(e,n,t);else if(e.child!==null){e.child.return=e,e=e.child;continue}if(e===t)break e;for(;e.sibling===null;){if(e.return===null||e.return===t)break e;e=e.return}e.sibling.return=e.return,e=e.sibling}r&=1}if(Ce(Le,r),(t.mode&1)===0)t.memoizedState=null;else switch(i){case"forwards":for(n=t.child,i=null;n!==null;)e=n.alternate,e!==null&&rl(e)===null&&(i=n),n=n.sibling;n=i,n===null?(i=t.child,t.child=null):(i=n.sibling,n.sibling=null),Go(t,!1,i,n,l);break;case"backwards":for(n=null,i=t.child,t.child=null;i!==null;){if(e=i.alternate,e!==null&&rl(e)===null){t.child=i;break}e=i.sibling,i.sibling=n,n=i,i=e}Go(t,!0,n,null,l);break;case"together":Go(t,!1,null,null,void 0);break;default:t.memoizedState=null}return t.child}function dl(e,t){(t.mode&1)===0&&e!==null&&(e.alternate=null,t.alternate=null,t.flags|=2)}function ln(e,t,n){if(e!==null&&(t.dependencies=e.dependencies),$n|=t.lanes,(n&t.childLanes)===0)return null;if(e!==null&&t.child!==e.child)throw Error(f(153));if(t.child!==null){for(e=t.child,n=_n(e,e.pendingProps),t.child=n,n.return=t;e.sibling!==null;)e=e.sibling,n=n.sibling=_n(e,e.pendingProps),n.return=t;n.sibling=null}return t.child}function Fd(e,t,n){switch(t.tag){case 3:wu(t),pr();break;case 5:As(t);break;case 1:at(t.type)&&Ki(t);break;case 4:_o(t,t.stateNode.containerInfo);break;case 10:var r=t.type._context,i=t.memoizedProps.value;Ce(Ji,r._currentValue),r._currentValue=i;break;case 13:if(r=t.memoizedState,r!==null)return r.dehydrated!==null?(Ce(Le,Le.current&1),t.flags|=128,null):(n&t.child.childLanes)!==0?Su(e,t,n):(Ce(Le,Le.current&1),e=ln(e,t,n),e!==null?e.sibling:null);Ce(Le,Le.current&1);break;case 19:if(r=(n&t.childLanes)!==0,(e.flags&128)!==0){if(r)return Nu(e,t,n);t.flags|=128}if(i=t.memoizedState,i!==null&&(i.rendering=null,i.tail=null,i.lastEffect=null),Ce(Le,Le.current),r)break;return null;case 22:case 23:return t.lanes=0,vu(e,t,n)}return ln(e,t,n)}var Cu,qo,zu,Eu;Cu=function(e,t){for(var n=t.child;n!==null;){if(n.tag===5||n.tag===6)e.appendChild(n.stateNode);else if(n.tag!==4&&n.child!==null){n.child.return=n,n=n.child;continue}if(n===t)break;for(;n.sibling===null;){if(n.return===null||n.return===t)return;n=n.return}n.sibling.return=n.return,n=n.sibling}},qo=function(){},zu=function(e,t,n,r){var i=e.memoizedProps;if(i!==r){e=t.stateNode,Wn(Qt.current);var l=null;switch(n){case"input":i=Pt(e,i),r=Pt(e,r),l=[];break;case"select":i=F({},i,{value:void 0}),r=F({},r,{value:void 0}),l=[];break;case"textarea":i=lt(e,i),r=lt(e,r),l=[];break;default:typeof i.onClick!="function"&&typeof r.onClick=="function"&&(e.onclick=Qi)}vi(n,r);var a;n=null;for(y in i)if(!r.hasOwnProperty(y)&&i.hasOwnProperty(y)&&i[y]!=null)if(y==="style"){var u=i[y];for(a in u)u.hasOwnProperty(a)&&(n||(n={}),n[a]="")}else y!=="dangerouslySetInnerHTML"&&y!=="children"&&y!=="suppressContentEditableWarning"&&y!=="suppressHydrationWarning"&&y!=="autoFocus"&&(x.hasOwnProperty(y)?l||(l=[]):(l=l||[]).push(y,null));for(y in r){var d=r[y];if(u=i!=null?i[y]:void 0,r.hasOwnProperty(y)&&d!==u&&(d!=null||u!=null))if(y==="style")if(u){for(a in u)!u.hasOwnProperty(a)||d&&d.hasOwnProperty(a)||(n||(n={}),n[a]="");for(a in d)d.hasOwnProperty(a)&&u[a]!==d[a]&&(n||(n={}),n[a]=d[a])}else n||(l||(l=[]),l.push(y,n)),n=d;else y==="dangerouslySetInnerHTML"?(d=d?d.__html:void 0,u=u?u.__html:void 0,d!=null&&u!==d&&(l=l||[]).push(y,d)):y==="children"?typeof d!="string"&&typeof d!="number"||(l=l||[]).push(y,""+d):y!=="suppressContentEditableWarning"&&y!=="suppressHydrationWarning"&&(x.hasOwnProperty(y)?(d!=null&&y==="onScroll"&&Ee("scroll",e),l||u===d||(l=[])):(l=l||[]).push(y,d))}n&&(l=l||[]).push("style",n);var y=l;(t.updateQueue=y)&&(t.flags|=4)}},Eu=function(e,t,n,r){n!==r&&(t.flags|=4)};function ni(e,t){if(!Pe)switch(e.tailMode){case"hidden":t=e.tail;for(var n=null;t!==null;)t.alternate!==null&&(n=t),t=t.sibling;n===null?e.tail=null:n.sibling=null;break;case"collapsed":n=e.tail;for(var r=null;n!==null;)n.alternate!==null&&(r=n),n=n.sibling;r===null?t||e.tail===null?e.tail=null:e.tail.sibling=null:r.sibling=null}}function Je(e){var t=e.alternate!==null&&e.alternate.child===e.child,n=0,r=0;if(t)for(var i=e.child;i!==null;)n|=i.lanes|i.childLanes,r|=i.subtreeFlags&14680064,r|=i.flags&14680064,i.return=e,i=i.sibling;else for(i=e.child;i!==null;)n|=i.lanes|i.childLanes,r|=i.subtreeFlags,r|=i.flags,i.return=e,i=i.sibling;return e.subtreeFlags|=r,e.childLanes=n,t}function Rd(e,t,n){var r=t.pendingProps;switch(yo(t),t.tag){case 2:case 16:case 15:case 0:case 11:case 7:case 8:case 12:case 9:case 14:return Je(t),null;case 1:return at(t.type)&&Hi(),Je(t),null;case 3:return r=t.stateNode,vr(),_e(ot),_e(Xe),Do(),r.pendingContext&&(r.context=r.pendingContext,r.pendingContext=null),(e===null||e.child===null)&&(Xi(t)?t.flags|=4:e===null||e.memoizedState.isDehydrated&&(t.flags&256)===0||(t.flags|=1024,Ft!==null&&(aa(Ft),Ft=null))),qo(e,t),Je(t),null;case 5:Po(t);var i=Wn(Xr.current);if(n=t.type,e!==null&&t.stateNode!=null)zu(e,t,n,r,i),e.ref!==t.ref&&(t.flags|=512,t.flags|=2097152);else{if(!r){if(t.stateNode===null)throw Error(f(166));return Je(t),null}if(e=Wn(Qt.current),Xi(t)){r=t.stateNode,n=t.type;var l=t.memoizedProps;switch(r[Wt]=t,r[Hr]=l,e=(t.mode&1)!==0,n){case"dialog":Ee("cancel",r),Ee("close",r);break;case"iframe":case"object":case"embed":Ee("load",r);break;case"video":case"audio":for(i=0;i<Wr.length;i++)Ee(Wr[i],r);break;case"source":Ee("error",r);break;case"img":case"image":case"link":Ee("error",r),Ee("load",r);break;case"details":Ee("toggle",r);break;case"input":qe(r,l),Ee("invalid",r);break;case"select":r._wrapperState={wasMultiple:!!l.multiple},Ee("invalid",r);break;case"textarea":qn(r,l),Ee("invalid",r)}vi(n,l),i=null;for(var a in l)if(l.hasOwnProperty(a)){var u=l[a];a==="children"?typeof u=="string"?r.textContent!==u&&(l.suppressHydrationWarning!==!0&&Wi(r.textContent,u,e),i=["children",u]):typeof u=="number"&&r.textContent!==""+u&&(l.suppressHydrationWarning!==!0&&Wi(r.textContent,u,e),i=["children",""+u]):x.hasOwnProperty(a)&&u!=null&&a==="onScroll"&&Ee("scroll",r)}switch(n){case"input":it(r),Kt(r,l,!0);break;case"textarea":it(r),sn(r);break;case"select":case"option":break;default:typeof l.onClick=="function"&&(r.onclick=Qi)}r=i,t.updateQueue=r,r!==null&&(t.flags|=4)}else{a=i.nodeType===9?i:i.ownerDocument,e==="http://www.w3.org/1999/xhtml"&&(e=Zn(n)),e==="http://www.w3.org/1999/xhtml"?n==="script"?(e=a.createElement("div"),e.innerHTML="<script><\/script>",e=e.removeChild(e.firstChild)):typeof r.is=="string"?e=a.createElement(n,{is:r.is}):(e=a.createElement(n),n==="select"&&(a=e,r.multiple?a.multiple=!0:r.size&&(a.size=r.size))):e=a.createElementNS(e,n),e[Wt]=t,e[Hr]=r,Cu(e,t,!1,!1),t.stateNode=e;e:{switch(a=Nr(n,r),n){case"dialog":Ee("cancel",e),Ee("close",e),i=r;break;case"iframe":case"object":case"embed":Ee("load",e),i=r;break;case"video":case"audio":for(i=0;i<Wr.length;i++)Ee(Wr[i],e);i=r;break;case"source":Ee("error",e),i=r;break;case"img":case"image":case"link":Ee("error",e),Ee("load",e),i=r;break;case"details":Ee("toggle",e),i=r;break;case"input":qe(e,r),i=Pt(e,r),Ee("invalid",e);break;case"option":i=r;break;case"select":e._wrapperState={wasMultiple:!!r.multiple},i=F({},r,{value:void 0}),Ee("invalid",e);break;case"textarea":qn(e,r),i=lt(e,r),Ee("invalid",e);break;default:i=r}vi(n,i),u=i;for(l in u)if(u.hasOwnProperty(l)){var d=u[l];l==="style"?gi(e,d):l==="dangerouslySetInnerHTML"?(d=d?d.__html:void 0,d!=null&&Mn(e,d)):l==="children"?typeof d=="string"?(n!=="textarea"||d!=="")&&Gt(e,d):typeof d=="number"&&Gt(e,""+d):l!=="suppressContentEditableWarning"&&l!=="suppressHydrationWarning"&&l!=="autoFocus"&&(x.hasOwnProperty(l)?d!=null&&l==="onScroll"&&Ee("scroll",e):d!=null&&Ne(e,l,d,a))}switch(n){case"input":it(e),Kt(e,r,!1);break;case"textarea":it(e),sn(e);break;case"option":r.value!=null&&e.setAttribute("value",""+pe(r.value));break;case"select":e.multiple=!!r.multiple,l=r.value,l!=null?ft(e,!!r.multiple,l,!1):r.defaultValue!=null&&ft(e,!!r.multiple,r.defaultValue,!0);break;default:typeof i.onClick=="function"&&(e.onclick=Qi)}switch(n){case"button":case"input":case"select":case"textarea":r=!!r.autoFocus;break e;case"img":r=!0;break e;default:r=!1}}r&&(t.flags|=4)}t.ref!==null&&(t.flags|=512,t.flags|=2097152)}return Je(t),null;case 6:if(e&&t.stateNode!=null)Eu(e,t,e.memoizedProps,r);else{if(typeof r!="string"&&t.stateNode===null)throw Error(f(166));if(n=Wn(Xr.current),Wn(Qt.current),Xi(t)){if(r=t.stateNode,n=t.memoizedProps,r[Wt]=t,(l=r.nodeValue!==n)&&(e=ht,e!==null))switch(e.tag){case 3:Wi(r.nodeValue,n,(e.mode&1)!==0);break;case 5:e.memoizedProps.suppressHydrationWarning!==!0&&Wi(r.nodeValue,n,(e.mode&1)!==0)}l&&(t.flags|=4)}else r=(n.nodeType===9?n:n.ownerDocument).createTextNode(r),r[Wt]=t,t.stateNode=r}return Je(t),null;case 13:if(_e(Le),r=t.memoizedState,e===null||e.memoizedState!==null&&e.memoizedState.dehydrated!==null){if(Pe&&gt!==null&&(t.mode&1)!==0&&(t.flags&128)===0)Ls(),pr(),t.flags|=98560,l=!1;else if(l=Xi(t),r!==null&&r.dehydrated!==null){if(e===null){if(!l)throw Error(f(318));if(l=t.memoizedState,l=l!==null?l.dehydrated:null,!l)throw Error(f(317));l[Wt]=t}else pr(),(t.flags&128)===0&&(t.memoizedState=null),t.flags|=4;Je(t),l=!1}else Ft!==null&&(aa(Ft),Ft=null),l=!0;if(!l)return t.flags&65536?t:null}return(t.flags&128)!==0?(t.lanes=n,t):(r=r!==null,r!==(e!==null&&e.memoizedState!==null)&&r&&(t.child.flags|=8192,(t.mode&1)!==0&&(e===null||(Le.current&1)!==0?Ae===0&&(Ae=3):ca())),t.updateQueue!==null&&(t.flags|=4),Je(t),null);case 4:return vr(),qo(e,t),e===null&&Qr(t.stateNode.containerInfo),Je(t),null;case 10:return No(t.type._context),Je(t),null;case 17:return at(t.type)&&Hi(),Je(t),null;case 19:if(_e(Le),l=t.memoizedState,l===null)return Je(t),null;if(r=(t.flags&128)!==0,a=l.rendering,a===null)if(r)ni(l,!1);else{if(Ae!==0||e!==null&&(e.flags&128)!==0)for(e=t.child;e!==null;){if(a=rl(e),a!==null){for(t.flags|=128,ni(l,!1),r=a.updateQueue,r!==null&&(t.updateQueue=r,t.flags|=4),t.subtreeFlags=0,r=n,n=t.child;n!==null;)l=n,e=r,l.flags&=14680066,a=l.alternate,a===null?(l.childLanes=0,l.lanes=e,l.child=null,l.subtreeFlags=0,l.memoizedProps=null,l.memoizedState=null,l.updateQueue=null,l.dependencies=null,l.stateNode=null):(l.childLanes=a.childLanes,l.lanes=a.lanes,l.child=a.child,l.subtreeFlags=0,l.deletions=null,l.memoizedProps=a.memoizedProps,l.memoizedState=a.memoizedState,l.updateQueue=a.updateQueue,l.type=a.type,e=a.dependencies,l.dependencies=e===null?null:{lanes:e.lanes,firstContext:e.firstContext}),n=n.sibling;return Ce(Le,Le.current&1|2),t.child}e=e.sibling}l.tail!==null&&z()>kr&&(t.flags|=128,r=!0,ni(l,!1),t.lanes=4194304)}else{if(!r)if(e=rl(a),e!==null){if(t.flags|=128,r=!0,n=e.updateQueue,n!==null&&(t.updateQueue=n,t.flags|=4),ni(l,!0),l.tail===null&&l.tailMode==="hidden"&&!a.alternate&&!Pe)return Je(t),null}else 2*z()-l.renderingStartTime>kr&&n!==1073741824&&(t.flags|=128,r=!0,ni(l,!1),t.lanes=4194304);l.isBackwards?(a.sibling=t.child,t.child=a):(n=l.last,n!==null?n.sibling=a:t.child=a,l.last=a)}return l.tail!==null?(t=l.tail,l.rendering=t,l.tail=t.sibling,l.renderingStartTime=z(),t.sibling=null,n=Le.current,Ce(Le,r?n&1|2:n&1),t):(Je(t),null);case 22:case 23:return ua(),r=t.memoizedState!==null,e!==null&&e.memoizedState!==null!==r&&(t.flags|=8192),r&&(t.mode&1)!==0?(vt&1073741824)!==0&&(Je(t),t.subtreeFlags&6&&(t.flags|=8192)):Je(t),null;case 24:return null;case 25:return null}throw Error(f(156,t.tag))}function Id(e,t){switch(yo(t),t.tag){case 1:return at(t.type)&&Hi(),e=t.flags,e&65536?(t.flags=e&-65537|128,t):null;case 3:return vr(),_e(ot),_e(Xe),Do(),e=t.flags,(e&65536)!==0&&(e&128)===0?(t.flags=e&-65537|128,t):null;case 5:return Po(t),null;case 13:if(_e(Le),e=t.memoizedState,e!==null&&e.dehydrated!==null){if(t.alternate===null)throw Error(f(340));pr()}return e=t.flags,e&65536?(t.flags=e&-65537|128,t):null;case 19:return _e(Le),null;case 4:return vr(),null;case 10:return No(t.type._context),null;case 22:case 23:return ua(),null;case 24:return null;default:return null}}var fl=!1,et=!1,Od=typeof WeakSet=="function"?WeakSet:Set,R=null;function xr(e,t){var n=e.ref;if(n!==null)if(typeof n=="function")try{n(null)}catch(r){Te(e,t,r)}else n.current=null}function Xo(e,t,n){try{n()}catch(r){Te(e,t,r)}}var _u=!1;function Ad(e,t){if(so=Mi,e=os(),eo(e)){if("selectionStart"in e)var n={start:e.selectionStart,end:e.selectionEnd};else e:{n=(n=e.ownerDocument)&&n.defaultView||window;var r=n.getSelection&&n.getSelection();if(r&&r.rangeCount!==0){n=r.anchorNode;var i=r.anchorOffset,l=r.focusNode;r=r.focusOffset;try{n.nodeType,l.nodeType}catch{n=null;break e}var a=0,u=-1,d=-1,y=0,j=0,C=e,S=null;t:for(;;){for(var M;C!==n||i!==0&&C.nodeType!==3||(u=a+i),C!==l||r!==0&&C.nodeType!==3||(d=a+r),C.nodeType===3&&(a+=C.nodeValue.length),(M=C.firstChild)!==null;)S=C,C=M;for(;;){if(C===e)break t;if(S===n&&++y===i&&(u=a),S===l&&++j===r&&(d=a),(M=C.nextSibling)!==null)break;C=S,S=C.parentNode}C=M}n=u===-1||d===-1?null:{start:u,end:d}}else n=null}n=n||{start:0,end:0}}else n=null;for(uo={focusedElem:e,selectionRange:n},Mi=!1,R=t;R!==null;)if(t=R,e=t.child,(t.subtreeFlags&1028)!==0&&e!==null)e.return=t,R=e;else for(;R!==null;){t=R;try{var I=t.alternate;if((t.flags&1024)!==0)switch(t.tag){case 0:case 11:case 15:break;case 1:if(I!==null){var A=I.memoizedProps,Re=I.memoizedState,g=t.stateNode,p=g.getSnapshotBeforeUpdate(t.elementType===t.type?A:Rt(t.type,A),Re);g.__reactInternalSnapshotBeforeUpdate=p}break;case 3:var v=t.stateNode.containerInfo;v.nodeType===1?v.textContent="":v.nodeType===9&&v.documentElement&&v.removeChild(v.documentElement);break;case 5:case 6:case 4:case 17:break;default:throw Error(f(163))}}catch(_){Te(t,t.return,_)}if(e=t.sibling,e!==null){e.return=t.return,R=e;break}R=t.return}return I=_u,_u=!1,I}function ri(e,t,n){var r=t.updateQueue;if(r=r!==null?r.lastEffect:null,r!==null){var i=r=r.next;do{if((i.tag&e)===e){var l=i.destroy;i.destroy=void 0,l!==void 0&&Xo(t,n,l)}i=i.next}while(i!==r)}}function pl(e,t){if(t=t.updateQueue,t=t!==null?t.lastEffect:null,t!==null){var n=t=t.next;do{if((n.tag&e)===e){var r=n.create;n.destroy=r()}n=n.next}while(n!==t)}}function Zo(e){var t=e.ref;if(t!==null){var n=e.stateNode;switch(e.tag){case 5:e=n;break;default:e=n}typeof t=="function"?t(e):t.current=e}}function Pu(e){var t=e.alternate;t!==null&&(e.alternate=null,Pu(t)),e.child=null,e.deletions=null,e.sibling=null,e.tag===5&&(t=e.stateNode,t!==null&&(delete t[Wt],delete t[Hr],delete t[mo],delete t[wd],delete t[kd])),e.stateNode=null,e.return=null,e.dependencies=null,e.memoizedProps=null,e.memoizedState=null,e.pendingProps=null,e.stateNode=null,e.updateQueue=null}function Lu(e){return e.tag===5||e.tag===3||e.tag===4}function Du(e){e:for(;;){for(;e.sibling===null;){if(e.return===null||Lu(e.return))return null;e=e.return}for(e.sibling.return=e.return,e=e.sibling;e.tag!==5&&e.tag!==6&&e.tag!==18;){if(e.flags&2||e.child===null||e.tag===4)continue e;e.child.return=e,e=e.child}if(!(e.flags&2))return e.stateNode}}function Jo(e,t,n){var r=e.tag;if(r===5||r===6)e=e.stateNode,t?n.nodeType===8?n.parentNode.insertBefore(e,t):n.insertBefore(e,t):(n.nodeType===8?(t=n.parentNode,t.insertBefore(e,n)):(t=n,t.appendChild(e)),n=n._reactRootContainer,n!=null||t.onclick!==null||(t.onclick=Qi));else if(r!==4&&(e=e.child,e!==null))for(Jo(e,t,n),e=e.sibling;e!==null;)Jo(e,t,n),e=e.sibling}function ea(e,t,n){var r=e.tag;if(r===5||r===6)e=e.stateNode,t?n.insertBefore(e,t):n.appendChild(e);else if(r!==4&&(e=e.child,e!==null))for(ea(e,t,n),e=e.sibling;e!==null;)ea(e,t,n),e=e.sibling}var Qe=null,It=!1;function jn(e,t,n){for(n=n.child;n!==null;)Mu(e,t,n),n=n.sibling}function Mu(e,t,n){if(bt&&typeof bt.onCommitFiberUnmount=="function")try{bt.onCommitFiberUnmount(cn,n)}catch{}switch(n.tag){case 5:et||xr(n,t);case 6:var r=Qe,i=It;Qe=null,jn(e,t,n),Qe=r,It=i,Qe!==null&&(It?(e=Qe,n=n.stateNode,e.nodeType===8?e.parentNode.removeChild(n):e.removeChild(n)):Qe.removeChild(n.stateNode));break;case 18:Qe!==null&&(It?(e=Qe,n=n.stateNode,e.nodeType===8?po(e.parentNode,n):e.nodeType===1&&po(e,n),Rr(e)):po(Qe,n.stateNode));break;case 4:r=Qe,i=It,Qe=n.stateNode.containerInfo,It=!0,jn(e,t,n),Qe=r,It=i;break;case 0:case 11:case 14:case 15:if(!et&&(r=n.updateQueue,r!==null&&(r=r.lastEffect,r!==null))){i=r=r.next;do{var l=i,a=l.destroy;l=l.tag,a!==void 0&&((l&2)!==0||(l&4)!==0)&&Xo(n,t,a),i=i.next}while(i!==r)}jn(e,t,n);break;case 1:if(!et&&(xr(n,t),r=n.stateNode,typeof r.componentWillUnmount=="function"))try{r.props=n.memoizedProps,r.state=n.memoizedState,r.componentWillUnmount()}catch(u){Te(n,t,u)}jn(e,t,n);break;case 21:jn(e,t,n);break;case 22:n.mode&1?(et=(r=et)||n.memoizedState!==null,jn(e,t,n),et=r):jn(e,t,n);break;default:jn(e,t,n)}}function Tu(e){var t=e.updateQueue;if(t!==null){e.updateQueue=null;var n=e.stateNode;n===null&&(n=e.stateNode=new Od),t.forEach(function(r){var i=Kd.bind(null,e,r);n.has(r)||(n.add(r),r.then(i,i))})}}function Ot(e,t){var n=t.deletions;if(n!==null)for(var r=0;r<n.length;r++){var i=n[r];try{var l=e,a=t,u=a;e:for(;u!==null;){switch(u.tag){case 5:Qe=u.stateNode,It=!1;break e;case 3:Qe=u.stateNode.containerInfo,It=!0;break e;case 4:Qe=u.stateNode.containerInfo,It=!0;break e}u=u.return}if(Qe===null)throw Error(f(160));Mu(l,a,i),Qe=null,It=!1;var d=i.alternate;d!==null&&(d.return=null),i.return=null}catch(y){Te(i,t,y)}}if(t.subtreeFlags&12854)for(t=t.child;t!==null;)Fu(t,e),t=t.sibling}function Fu(e,t){var n=e.alternate,r=e.flags;switch(e.tag){case 0:case 11:case 14:case 15:if(Ot(t,e),Ht(e),r&4){try{ri(3,e,e.return),pl(3,e)}catch(A){Te(e,e.return,A)}try{ri(5,e,e.return)}catch(A){Te(e,e.return,A)}}break;case 1:Ot(t,e),Ht(e),r&512&&n!==null&&xr(n,n.return);break;case 5:if(Ot(t,e),Ht(e),r&512&&n!==null&&xr(n,n.return),e.flags&32){var i=e.stateNode;try{Gt(i,"")}catch(A){Te(e,e.return,A)}}if(r&4&&(i=e.stateNode,i!=null)){var l=e.memoizedProps,a=n!==null?n.memoizedProps:l,u=e.type,d=e.updateQueue;if(e.updateQueue=null,d!==null)try{u==="input"&&l.type==="radio"&&l.name!=null&&Lt(i,l),Nr(u,a);var y=Nr(u,l);for(a=0;a<d.length;a+=2){var j=d[a],C=d[a+1];j==="style"?gi(i,C):j==="dangerouslySetInnerHTML"?Mn(i,C):j==="children"?Gt(i,C):Ne(i,j,C,y)}switch(u){case"input":yt(i,l);break;case"textarea":Xn(i,l);break;case"select":var S=i._wrapperState.wasMultiple;i._wrapperState.wasMultiple=!!l.multiple;var M=l.value;M!=null?ft(i,!!l.multiple,M,!1):S!==!!l.multiple&&(l.defaultValue!=null?ft(i,!!l.multiple,l.defaultValue,!0):ft(i,!!l.multiple,l.multiple?[]:"",!1))}i[Hr]=l}catch(A){Te(e,e.return,A)}}break;case 6:if(Ot(t,e),Ht(e),r&4){if(e.stateNode===null)throw Error(f(162));i=e.stateNode,l=e.memoizedProps;try{i.nodeValue=l}catch(A){Te(e,e.return,A)}}break;case 3:if(Ot(t,e),Ht(e),r&4&&n!==null&&n.memoizedState.isDehydrated)try{Rr(t.containerInfo)}catch(A){Te(e,e.return,A)}break;case 4:Ot(t,e),Ht(e);break;case 13:Ot(t,e),Ht(e),i=e.child,i.flags&8192&&(l=i.memoizedState!==null,i.stateNode.isHidden=l,!l||i.alternate!==null&&i.alternate.memoizedState!==null||(ra=z())),r&4&&Tu(e);break;case 22:if(j=n!==null&&n.memoizedState!==null,e.mode&1?(et=(y=et)||j,Ot(t,e),et=y):Ot(t,e),Ht(e),r&8192){if(y=e.memoizedState!==null,(e.stateNode.isHidden=y)&&!j&&(e.mode&1)!==0)for(R=e,j=e.child;j!==null;){for(C=R=j;R!==null;){switch(S=R,M=S.child,S.tag){case 0:case 11:case 14:case 15:ri(4,S,S.return);break;case 1:xr(S,S.return);var I=S.stateNode;if(typeof I.componentWillUnmount=="function"){r=S,n=S.return;try{t=r,I.props=t.memoizedProps,I.state=t.memoizedState,I.componentWillUnmount()}catch(A){Te(r,n,A)}}break;case 5:xr(S,S.return);break;case 22:if(S.memoizedState!==null){Ou(C);continue}}M!==null?(M.return=S,R=M):Ou(C)}j=j.sibling}e:for(j=null,C=e;;){if(C.tag===5){if(j===null){j=C;try{i=C.stateNode,y?(l=i.style,typeof l.setProperty=="function"?l.setProperty("display","none","important"):l.display="none"):(u=C.stateNode,d=C.memoizedProps.style,a=d!=null&&d.hasOwnProperty("display")?d.display:null,u.style.display=jr("display",a))}catch(A){Te(e,e.return,A)}}}else if(C.tag===6){if(j===null)try{C.stateNode.nodeValue=y?"":C.memoizedProps}catch(A){Te(e,e.return,A)}}else if((C.tag!==22&&C.tag!==23||C.memoizedState===null||C===e)&&C.child!==null){C.child.return=C,C=C.child;continue}if(C===e)break e;for(;C.sibling===null;){if(C.return===null||C.return===e)break e;j===C&&(j=null),C=C.return}j===C&&(j=null),C.sibling.return=C.return,C=C.sibling}}break;case 19:Ot(t,e),Ht(e),r&4&&Tu(e);break;case 21:break;default:Ot(t,e),Ht(e)}}function Ht(e){var t=e.flags;if(t&2){try{e:{for(var n=e.return;n!==null;){if(Lu(n)){var r=n;break e}n=n.return}throw Error(f(160))}switch(r.tag){case 5:var i=r.stateNode;r.flags&32&&(Gt(i,""),r.flags&=-33);var l=Du(e);ea(e,l,i);break;case 3:case 4:var a=r.stateNode.containerInfo,u=Du(e);Jo(e,u,a);break;default:throw Error(f(161))}}catch(d){Te(e,e.return,d)}e.flags&=-3}t&4096&&(e.flags&=-4097)}function Ud(e,t,n){R=e,Ru(e)}function Ru(e,t,n){for(var r=(e.mode&1)!==0;R!==null;){var i=R,l=i.child;if(i.tag===22&&r){var a=i.memoizedState!==null||fl;if(!a){var u=i.alternate,d=u!==null&&u.memoizedState!==null||et;u=fl;var y=et;if(fl=a,(et=d)&&!y)for(R=i;R!==null;)a=R,d=a.child,a.tag===22&&a.memoizedState!==null?Au(i):d!==null?(d.return=a,R=d):Au(i);for(;l!==null;)R=l,Ru(l),l=l.sibling;R=i,fl=u,et=y}Iu(e)}else(i.subtreeFlags&8772)!==0&&l!==null?(l.return=i,R=l):Iu(e)}}function Iu(e){for(;R!==null;){var t=R;if((t.flags&8772)!==0){var n=t.alternate;try{if((t.flags&8772)!==0)switch(t.tag){case 0:case 11:case 15:et||pl(5,t);break;case 1:var r=t.stateNode;if(t.flags&4&&!et)if(n===null)r.componentDidMount();else{var i=t.elementType===t.type?n.memoizedProps:Rt(t.type,n.memoizedProps);r.componentDidUpdate(i,n.memoizedState,r.__reactInternalSnapshotBeforeUpdate)}var l=t.updateQueue;l!==null&&Os(t,l,r);break;case 3:var a=t.updateQueue;if(a!==null){if(n=null,t.child!==null)switch(t.child.tag){case 5:n=t.child.stateNode;break;case 1:n=t.child.stateNode}Os(t,a,n)}break;case 5:var u=t.stateNode;if(n===null&&t.flags&4){n=u;var d=t.memoizedProps;switch(t.type){case"button":case"input":case"select":case"textarea":d.autoFocus&&n.focus();break;case"img":d.src&&(n.src=d.src)}}break;case 6:break;case 4:break;case 12:break;case 13:if(t.memoizedState===null){var y=t.alternate;if(y!==null){var j=y.memoizedState;if(j!==null){var C=j.dehydrated;C!==null&&Rr(C)}}}break;case 19:case 17:case 21:case 22:case 23:case 25:break;default:throw Error(f(163))}et||t.flags&512&&Zo(t)}catch(S){Te(t,t.return,S)}}if(t===e){R=null;break}if(n=t.sibling,n!==null){n.return=t.return,R=n;break}R=t.return}}function Ou(e){for(;R!==null;){var t=R;if(t===e){R=null;break}var n=t.sibling;if(n!==null){n.return=t.return,R=n;break}R=t.return}}function Au(e){for(;R!==null;){var t=R;try{switch(t.tag){case 0:case 11:case 15:var n=t.return;try{pl(4,t)}catch(d){Te(t,n,d)}break;case 1:var r=t.stateNode;if(typeof r.componentDidMount=="function"){var i=t.return;try{r.componentDidMount()}catch(d){Te(t,i,d)}}var l=t.return;try{Zo(t)}catch(d){Te(t,l,d)}break;case 5:var a=t.return;try{Zo(t)}catch(d){Te(t,a,d)}}}catch(d){Te(t,t.return,d)}if(t===e){R=null;break}var u=t.sibling;if(u!==null){u.return=t.return,R=u;break}R=t.return}}var Bd=Math.ceil,ml=de.ReactCurrentDispatcher,ta=de.ReactCurrentOwner,Et=de.ReactCurrentBatchConfig,ce=0,be=null,Ie=null,$e=0,vt=0,wr=yn(0),Ae=0,ii=null,$n=0,hl=0,na=0,li=null,ut=null,ra=0,kr=1/0,on=null,gl=!1,ia=null,Nn=null,vl=!1,Cn=null,yl=0,oi=0,la=null,xl=-1,wl=0;function rt(){return(ce&6)!==0?z():xl!==-1?xl:xl=z()}function zn(e){return(e.mode&1)===0?1:(ce&2)!==0&&$e!==0?$e&-$e:jd.transition!==null?(wl===0&&(wl=Da()),wl):(e=ge,e!==0||(e=window.event,e=e===void 0?16:Ba(e.type)),e)}function At(e,t,n,r){if(50<oi)throw oi=0,la=null,Error(f(185));Lr(e,n,r),((ce&2)===0||e!==be)&&(e===be&&((ce&2)===0&&(hl|=n),Ae===4&&En(e,$e)),ct(e,r),n===1&&ce===0&&(t.mode&1)===0&&(kr=z()+500,Yi&&wn()))}function ct(e,t){var n=e.callbackNode;jc(e,t);var r=Pi(e,e===be?$e:0);if(r===0)n!==null&&zi(n),e.callbackNode=null,e.callbackPriority=0;else if(t=r&-r,e.callbackPriority!==t){if(n!=null&&zi(n),t===1)e.tag===0?Sd(Bu.bind(null,e)):Cs(Bu.bind(null,e)),yd(function(){(ce&6)===0&&wn()}),n=null;else{switch(Ma(r)){case 1:n=ue;break;case 4:n=tt;break;case 16:n=ze;break;case 536870912:n=On;break;default:n=ze}n=Yu(n,Uu.bind(null,e))}e.callbackPriority=t,e.callbackNode=n}}function Uu(e,t){if(xl=-1,wl=0,(ce&6)!==0)throw Error(f(327));var n=e.callbackNode;if(Sr()&&e.callbackNode!==n)return null;var r=Pi(e,e===be?$e:0);if(r===0)return null;if((r&30)!==0||(r&e.expiredLanes)!==0||t)t=kl(e,r);else{t=r;var i=ce;ce|=2;var l=bu();(be!==e||$e!==t)&&(on=null,kr=z()+500,Kn(e,t));do try{Wd();break}catch(u){Vu(e,u)}while(!0);jo(),ml.current=l,ce=i,Ie!==null?t=0:(be=null,$e=0,t=Ae)}if(t!==0){if(t===2&&(i=Al(e),i!==0&&(r=i,t=oa(e,i))),t===1)throw n=ii,Kn(e,0),En(e,r),ct(e,z()),n;if(t===6)En(e,r);else{if(i=e.current.alternate,(r&30)===0&&!Vd(i)&&(t=kl(e,r),t===2&&(l=Al(e),l!==0&&(r=l,t=oa(e,l))),t===1))throw n=ii,Kn(e,0),En(e,r),ct(e,z()),n;switch(e.finishedWork=i,e.finishedLanes=r,t){case 0:case 1:throw Error(f(345));case 2:Yn(e,ut,on);break;case 3:if(En(e,r),(r&130023424)===r&&(t=ra+500-z(),10<t)){if(Pi(e,0)!==0)break;if(i=e.suspendedLanes,(i&r)!==r){rt(),e.pingedLanes|=e.suspendedLanes&i;break}e.timeoutHandle=fo(Yn.bind(null,e,ut,on),t);break}Yn(e,ut,on);break;case 4:if(En(e,r),(r&4194240)===r)break;for(t=e.eventTimes,i=-1;0<r;){var a=31-Mt(r);l=1<<a,a=t[a],a>i&&(i=a),r&=~l}if(r=i,r=z()-r,r=(120>r?120:480>r?480:1080>r?1080:1920>r?1920:3e3>r?3e3:4320>r?4320:1960*Bd(r/1960))-r,10<r){e.timeoutHandle=fo(Yn.bind(null,e,ut,on),r);break}Yn(e,ut,on);break;case 5:Yn(e,ut,on);break;default:throw Error(f(329))}}}return ct(e,z()),e.callbackNode===n?Uu.bind(null,e):null}function oa(e,t){var n=li;return e.current.memoizedState.isDehydrated&&(Kn(e,t).flags|=256),e=kl(e,t),e!==2&&(t=ut,ut=n,t!==null&&aa(t)),e}function aa(e){ut===null?ut=e:ut.push.apply(ut,e)}function Vd(e){for(var t=e;;){if(t.flags&16384){var n=t.updateQueue;if(n!==null&&(n=n.stores,n!==null))for(var r=0;r<n.length;r++){var i=n[r],l=i.getSnapshot;i=i.value;try{if(!Tt(l(),i))return!1}catch{return!1}}}if(n=t.child,t.subtreeFlags&16384&&n!==null)n.return=t,t=n;else{if(t===e)break;for(;t.sibling===null;){if(t.return===null||t.return===e)return!0;t=t.return}t.sibling.return=t.return,t=t.sibling}}return!0}function En(e,t){for(t&=~na,t&=~hl,e.suspendedLanes|=t,e.pingedLanes&=~t,e=e.expirationTimes;0<t;){var n=31-Mt(t),r=1<<n;e[n]=-1,t&=~r}}function Bu(e){if((ce&6)!==0)throw Error(f(327));Sr();var t=Pi(e,0);if((t&1)===0)return ct(e,z()),null;var n=kl(e,t);if(e.tag!==0&&n===2){var r=Al(e);r!==0&&(t=r,n=oa(e,r))}if(n===1)throw n=ii,Kn(e,0),En(e,t),ct(e,z()),n;if(n===6)throw Error(f(345));return e.finishedWork=e.current.alternate,e.finishedLanes=t,Yn(e,ut,on),ct(e,z()),null}function sa(e,t){var n=ce;ce|=1;try{return e(t)}finally{ce=n,ce===0&&(kr=z()+500,Yi&&wn())}}function Hn(e){Cn!==null&&Cn.tag===0&&(ce&6)===0&&Sr();var t=ce;ce|=1;var n=Et.transition,r=ge;try{if(Et.transition=null,ge=1,e)return e()}finally{ge=r,Et.transition=n,ce=t,(ce&6)===0&&wn()}}function ua(){vt=wr.current,_e(wr)}function Kn(e,t){e.finishedWork=null,e.finishedLanes=0;var n=e.timeoutHandle;if(n!==-1&&(e.timeoutHandle=-1,vd(n)),Ie!==null)for(n=Ie.return;n!==null;){var r=n;switch(yo(r),r.tag){case 1:r=r.type.childContextTypes,r!=null&&Hi();break;case 3:vr(),_e(ot),_e(Xe),Do();break;case 5:Po(r);break;case 4:vr();break;case 13:_e(Le);break;case 19:_e(Le);break;case 10:No(r.type._context);break;case 22:case 23:ua()}n=n.return}if(be=e,Ie=e=_n(e.current,null),$e=vt=t,Ae=0,ii=null,na=hl=$n=0,ut=li=null,bn!==null){for(t=0;t<bn.length;t++)if(n=bn[t],r=n.interleaved,r!==null){n.interleaved=null;var i=r.next,l=n.pending;if(l!==null){var a=l.next;l.next=i,r.next=a}n.pending=r}bn=null}return e}function Vu(e,t){do{var n=Ie;try{if(jo(),il.current=sl,ll){for(var r=De.memoizedState;r!==null;){var i=r.queue;i!==null&&(i.pending=null),r=r.next}ll=!1}if(Qn=0,Ve=Oe=De=null,Zr=!1,Jr=0,ta.current=null,n===null||n.return===null){Ae=1,ii=t,Ie=null;break}e:{var l=e,a=n.return,u=n,d=t;if(t=$e,u.flags|=32768,d!==null&&typeof d=="object"&&typeof d.then=="function"){var y=d,j=u,C=j.tag;if((j.mode&1)===0&&(C===0||C===11||C===15)){var S=j.alternate;S?(j.updateQueue=S.updateQueue,j.memoizedState=S.memoizedState,j.lanes=S.lanes):(j.updateQueue=null,j.memoizedState=null)}var M=fu(a);if(M!==null){M.flags&=-257,pu(M,a,u,l,t),M.mode&1&&du(l,y,t),t=M,d=y;var I=t.updateQueue;if(I===null){var A=new Set;A.add(d),t.updateQueue=A}else I.add(d);break e}else{if((t&1)===0){du(l,y,t),ca();break e}d=Error(f(426))}}else if(Pe&&u.mode&1){var Re=fu(a);if(Re!==null){(Re.flags&65536)===0&&(Re.flags|=256),pu(Re,a,u,l,t),ko(yr(d,u));break e}}l=d=yr(d,u),Ae!==4&&(Ae=2),li===null?li=[l]:li.push(l),l=a;do{switch(l.tag){case 3:l.flags|=65536,t&=-t,l.lanes|=t;var g=uu(l,d,t);Is(l,g);break e;case 1:u=d;var p=l.type,v=l.stateNode;if((l.flags&128)===0&&(typeof p.getDerivedStateFromError=="function"||v!==null&&typeof v.componentDidCatch=="function"&&(Nn===null||!Nn.has(v)))){l.flags|=65536,t&=-t,l.lanes|=t;var _=cu(l,u,t);Is(l,_);break e}}l=l.return}while(l!==null)}Qu(n)}catch(V){t=V,Ie===n&&n!==null&&(Ie=n=n.return);continue}break}while(!0)}function bu(){var e=ml.current;return ml.current=sl,e===null?sl:e}function ca(){(Ae===0||Ae===3||Ae===2)&&(Ae=4),be===null||($n&268435455)===0&&(hl&268435455)===0||En(be,$e)}function kl(e,t){var n=ce;ce|=2;var r=bu();(be!==e||$e!==t)&&(on=null,Kn(e,t));do try{bd();break}catch(i){Vu(e,i)}while(!0);if(jo(),ce=n,ml.current=r,Ie!==null)throw Error(f(261));return be=null,$e=0,Ae}function bd(){for(;Ie!==null;)Wu(Ie)}function Wd(){for(;Ie!==null&&!c();)Wu(Ie)}function Wu(e){var t=Ku(e.alternate,e,vt);e.memoizedProps=e.pendingProps,t===null?Qu(e):Ie=t,ta.current=null}function Qu(e){var t=e;do{var n=t.alternate;if(e=t.return,(t.flags&32768)===0){if(n=Rd(n,t,vt),n!==null){Ie=n;return}}else{if(n=Id(n,t),n!==null){n.flags&=32767,Ie=n;return}if(e!==null)e.flags|=32768,e.subtreeFlags=0,e.deletions=null;else{Ae=6,Ie=null;return}}if(t=t.sibling,t!==null){Ie=t;return}Ie=t=e}while(t!==null);Ae===0&&(Ae=5)}function Yn(e,t,n){var r=ge,i=Et.transition;try{Et.transition=null,ge=1,Qd(e,t,n,r)}finally{Et.transition=i,ge=r}return null}function Qd(e,t,n,r){do Sr();while(Cn!==null);if((ce&6)!==0)throw Error(f(327));n=e.finishedWork;var i=e.finishedLanes;if(n===null)return null;if(e.finishedWork=null,e.finishedLanes=0,n===e.current)throw Error(f(177));e.callbackNode=null,e.callbackPriority=0;var l=n.lanes|n.childLanes;if(Nc(e,l),e===be&&(Ie=be=null,$e=0),(n.subtreeFlags&2064)===0&&(n.flags&2064)===0||vl||(vl=!0,Yu(ze,function(){return Sr(),null})),l=(n.flags&15990)!==0,(n.subtreeFlags&15990)!==0||l){l=Et.transition,Et.transition=null;var a=ge;ge=1;var u=ce;ce|=4,ta.current=null,Ad(e,n),Fu(n,e),cd(uo),Mi=!!so,uo=so=null,e.current=n,Ud(n),N(),ce=u,ge=a,Et.transition=l}else e.current=n;if(vl&&(vl=!1,Cn=e,yl=i),l=e.pendingLanes,l===0&&(Nn=null),yc(n.stateNode),ct(e,z()),t!==null)for(r=e.onRecoverableError,n=0;n<t.length;n++)i=t[n],r(i.value,{componentStack:i.stack,digest:i.digest});if(gl)throw gl=!1,e=ia,ia=null,e;return(yl&1)!==0&&e.tag!==0&&Sr(),l=e.pendingLanes,(l&1)!==0?e===la?oi++:(oi=0,la=e):oi=0,wn(),null}function Sr(){if(Cn!==null){var e=Ma(yl),t=Et.transition,n=ge;try{if(Et.transition=null,ge=16>e?16:e,Cn===null)var r=!1;else{if(e=Cn,Cn=null,yl=0,(ce&6)!==0)throw Error(f(331));var i=ce;for(ce|=4,R=e.current;R!==null;){var l=R,a=l.child;if((R.flags&16)!==0){var u=l.deletions;if(u!==null){for(var d=0;d<u.length;d++){var y=u[d];for(R=y;R!==null;){var j=R;switch(j.tag){case 0:case 11:case 15:ri(8,j,l)}var C=j.child;if(C!==null)C.return=j,R=C;else for(;R!==null;){j=R;var S=j.sibling,M=j.return;if(Pu(j),j===y){R=null;break}if(S!==null){S.return=M,R=S;break}R=M}}}var I=l.alternate;if(I!==null){var A=I.child;if(A!==null){I.child=null;do{var Re=A.sibling;A.sibling=null,A=Re}while(A!==null)}}R=l}}if((l.subtreeFlags&2064)!==0&&a!==null)a.return=l,R=a;else e:for(;R!==null;){if(l=R,(l.flags&2048)!==0)switch(l.tag){case 0:case 11:case 15:ri(9,l,l.return)}var g=l.sibling;if(g!==null){g.return=l.return,R=g;break e}R=l.return}}var p=e.current;for(R=p;R!==null;){a=R;var v=a.child;if((a.subtreeFlags&2064)!==0&&v!==null)v.return=a,R=v;else e:for(a=p;R!==null;){if(u=R,(u.flags&2048)!==0)try{switch(u.tag){case 0:case 11:case 15:pl(9,u)}}catch(V){Te(u,u.return,V)}if(u===a){R=null;break e}var _=u.sibling;if(_!==null){_.return=u.return,R=_;break e}R=u.return}}if(ce=i,wn(),bt&&typeof bt.onPostCommitFiberRoot=="function")try{bt.onPostCommitFiberRoot(cn,e)}catch{}r=!0}return r}finally{ge=n,Et.transition=t}}return!1}function $u(e,t,n){t=yr(n,t),t=uu(e,t,1),e=Sn(e,t,1),t=rt(),e!==null&&(Lr(e,1,t),ct(e,t))}function Te(e,t,n){if(e.tag===3)$u(e,e,n);else for(;t!==null;){if(t.tag===3){$u(t,e,n);break}else if(t.tag===1){var r=t.stateNode;if(typeof t.type.getDerivedStateFromError=="function"||typeof r.componentDidCatch=="function"&&(Nn===null||!Nn.has(r))){e=yr(n,e),e=cu(t,e,1),t=Sn(t,e,1),e=rt(),t!==null&&(Lr(t,1,e),ct(t,e));break}}t=t.return}}function $d(e,t,n){var r=e.pingCache;r!==null&&r.delete(t),t=rt(),e.pingedLanes|=e.suspendedLanes&n,be===e&&($e&n)===n&&(Ae===4||Ae===3&&($e&130023424)===$e&&500>z()-ra?Kn(e,0):na|=n),ct(e,t)}function Hu(e,t){t===0&&((e.mode&1)===0?t=1:(t=_i,_i<<=1,(_i&130023424)===0&&(_i=4194304)));var n=rt();e=nn(e,t),e!==null&&(Lr(e,t,n),ct(e,n))}function Hd(e){var t=e.memoizedState,n=0;t!==null&&(n=t.retryLane),Hu(e,n)}function Kd(e,t){var n=0;switch(e.tag){case 13:var r=e.stateNode,i=e.memoizedState;i!==null&&(n=i.retryLane);break;case 19:r=e.stateNode;break;default:throw Error(f(314))}r!==null&&r.delete(t),Hu(e,n)}var Ku;Ku=function(e,t,n){if(e!==null)if(e.memoizedProps!==t.pendingProps||ot.current)st=!0;else{if((e.lanes&n)===0&&(t.flags&128)===0)return st=!1,Fd(e,t,n);st=(e.flags&131072)!==0}else st=!1,Pe&&(t.flags&1048576)!==0&&zs(t,qi,t.index);switch(t.lanes=0,t.tag){case 2:var r=t.type;dl(e,t),e=t.pendingProps;var i=cr(t,Xe.current);gr(t,n),i=Fo(null,t,r,e,i,n);var l=Ro();return t.flags|=1,typeof i=="object"&&i!==null&&typeof i.render=="function"&&i.$$typeof===void 0?(t.tag=1,t.memoizedState=null,t.updateQueue=null,at(r)?(l=!0,Ki(t)):l=!1,t.memoizedState=i.state!==null&&i.state!==void 0?i.state:null,Eo(t),i.updater=ul,t.stateNode=i,i._reactInternals=t,Vo(t,r,e,n),t=$o(null,t,r,!0,l,n)):(t.tag=0,Pe&&l&&vo(t),nt(null,t,i,n),t=t.child),t;case 16:r=t.elementType;e:{switch(dl(e,t),e=t.pendingProps,i=r._init,r=i(r._payload),t.type=r,i=t.tag=Gd(r),e=Rt(r,e),i){case 0:t=Qo(null,t,r,e,n);break e;case 1:t=xu(null,t,r,e,n);break e;case 11:t=mu(null,t,r,e,n);break e;case 14:t=hu(null,t,r,Rt(r.type,e),n);break e}throw Error(f(306,r,""))}return t;case 0:return r=t.type,i=t.pendingProps,i=t.elementType===r?i:Rt(r,i),Qo(e,t,r,i,n);case 1:return r=t.type,i=t.pendingProps,i=t.elementType===r?i:Rt(r,i),xu(e,t,r,i,n);case 3:e:{if(wu(t),e===null)throw Error(f(387));r=t.pendingProps,l=t.memoizedState,i=l.element,Rs(e,t),nl(t,r,null,n);var a=t.memoizedState;if(r=a.element,l.isDehydrated)if(l={element:r,isDehydrated:!1,cache:a.cache,pendingSuspenseBoundaries:a.pendingSuspenseBoundaries,transitions:a.transitions},t.updateQueue.baseState=l,t.memoizedState=l,t.flags&256){i=yr(Error(f(423)),t),t=ku(e,t,r,n,i);break e}else if(r!==i){i=yr(Error(f(424)),t),t=ku(e,t,r,n,i);break e}else for(gt=vn(t.stateNode.containerInfo.firstChild),ht=t,Pe=!0,Ft=null,n=Ts(t,null,r,n),t.child=n;n;)n.flags=n.flags&-3|4096,n=n.sibling;else{if(pr(),r===i){t=ln(e,t,n);break e}nt(e,t,r,n)}t=t.child}return t;case 5:return As(t),e===null&&wo(t),r=t.type,i=t.pendingProps,l=e!==null?e.memoizedProps:null,a=i.children,co(r,i)?a=null:l!==null&&co(r,l)&&(t.flags|=32),yu(e,t),nt(e,t,a,n),t.child;case 6:return e===null&&wo(t),null;case 13:return Su(e,t,n);case 4:return _o(t,t.stateNode.containerInfo),r=t.pendingProps,e===null?t.child=mr(t,null,r,n):nt(e,t,r,n),t.child;case 11:return r=t.type,i=t.pendingProps,i=t.elementType===r?i:Rt(r,i),mu(e,t,r,i,n);case 7:return nt(e,t,t.pendingProps,n),t.child;case 8:return nt(e,t,t.pendingProps.children,n),t.child;case 12:return nt(e,t,t.pendingProps.children,n),t.child;case 10:e:{if(r=t.type._context,i=t.pendingProps,l=t.memoizedProps,a=i.value,Ce(Ji,r._currentValue),r._currentValue=a,l!==null)if(Tt(l.value,a)){if(l.children===i.children&&!ot.current){t=ln(e,t,n);break e}}else for(l=t.child,l!==null&&(l.return=t);l!==null;){var u=l.dependencies;if(u!==null){a=l.child;for(var d=u.firstContext;d!==null;){if(d.context===r){if(l.tag===1){d=rn(-1,n&-n),d.tag=2;var y=l.updateQueue;if(y!==null){y=y.shared;var j=y.pending;j===null?d.next=d:(d.next=j.next,j.next=d),y.pending=d}}l.lanes|=n,d=l.alternate,d!==null&&(d.lanes|=n),Co(l.return,n,t),u.lanes|=n;break}d=d.next}}else if(l.tag===10)a=l.type===t.type?null:l.child;else if(l.tag===18){if(a=l.return,a===null)throw Error(f(341));a.lanes|=n,u=a.alternate,u!==null&&(u.lanes|=n),Co(a,n,t),a=l.sibling}else a=l.child;if(a!==null)a.return=l;else for(a=l;a!==null;){if(a===t){a=null;break}if(l=a.sibling,l!==null){l.return=a.return,a=l;break}a=a.return}l=a}nt(e,t,i.children,n),t=t.child}return t;case 9:return i=t.type,r=t.pendingProps.children,gr(t,n),i=Ct(i),r=r(i),t.flags|=1,nt(e,t,r,n),t.child;case 14:return r=t.type,i=Rt(r,t.pendingProps),i=Rt(r.type,i),hu(e,t,r,i,n);case 15:return gu(e,t,t.type,t.pendingProps,n);case 17:return r=t.type,i=t.pendingProps,i=t.elementType===r?i:Rt(r,i),dl(e,t),t.tag=1,at(r)?(e=!0,Ki(t)):e=!1,gr(t,n),au(t,r,i),Vo(t,r,i,n),$o(null,t,r,!0,e,n);case 19:return Nu(e,t,n);case 22:return vu(e,t,n)}throw Error(f(156,t.tag))};function Yu(e,t){return Ci(e,t)}function Yd(e,t,n,r){this.tag=e,this.key=n,this.sibling=this.child=this.return=this.stateNode=this.type=this.elementType=null,this.index=0,this.ref=null,this.pendingProps=t,this.dependencies=this.memoizedState=this.updateQueue=this.memoizedProps=null,this.mode=r,this.subtreeFlags=this.flags=0,this.deletions=null,this.childLanes=this.lanes=0,this.alternate=null}function _t(e,t,n,r){return new Yd(e,t,n,r)}function da(e){return e=e.prototype,!(!e||!e.isReactComponent)}function Gd(e){if(typeof e=="function")return da(e)?1:0;if(e!=null){if(e=e.$$typeof,e===ye)return 11;if(e===ae)return 14}return 2}function _n(e,t){var n=e.alternate;return n===null?(n=_t(e.tag,t,e.key,e.mode),n.elementType=e.elementType,n.type=e.type,n.stateNode=e.stateNode,n.alternate=e,e.alternate=n):(n.pendingProps=t,n.type=e.type,n.flags=0,n.subtreeFlags=0,n.deletions=null),n.flags=e.flags&14680064,n.childLanes=e.childLanes,n.lanes=e.lanes,n.child=e.child,n.memoizedProps=e.memoizedProps,n.memoizedState=e.memoizedState,n.updateQueue=e.updateQueue,t=e.dependencies,n.dependencies=t===null?null:{lanes:t.lanes,firstContext:t.firstContext},n.sibling=e.sibling,n.index=e.index,n.ref=e.ref,n}function Sl(e,t,n,r,i,l){var a=2;if(r=e,typeof e=="function")da(e)&&(a=1);else if(typeof e=="string")a=5;else e:switch(e){case ke:return Gn(n.children,i,l,t);case Ue:a=8,i|=8;break;case Ke:return e=_t(12,n,t,i|2),e.elementType=Ke,e.lanes=l,e;case D:return e=_t(13,n,t,i),e.elementType=D,e.lanes=l,e;case Z:return e=_t(19,n,t,i),e.elementType=Z,e.lanes=l,e;case G:return jl(n,i,l,t);default:if(typeof e=="object"&&e!==null)switch(e.$$typeof){case Ye:a=10;break e;case $:a=9;break e;case ye:a=11;break e;case ae:a=14;break e;case se:a=16,r=null;break e}throw Error(f(130,e==null?e:typeof e,""))}return t=_t(a,n,t,i),t.elementType=e,t.type=r,t.lanes=l,t}function Gn(e,t,n,r){return e=_t(7,e,r,t),e.lanes=n,e}function jl(e,t,n,r){return e=_t(22,e,r,t),e.elementType=G,e.lanes=n,e.stateNode={isHidden:!1},e}function fa(e,t,n){return e=_t(6,e,null,t),e.lanes=n,e}function pa(e,t,n){return t=_t(4,e.children!==null?e.children:[],e.key,t),t.lanes=n,t.stateNode={containerInfo:e.containerInfo,pendingChildren:null,implementation:e.implementation},t}function qd(e,t,n,r,i){this.tag=t,this.containerInfo=e,this.finishedWork=this.pingCache=this.current=this.pendingChildren=null,this.timeoutHandle=-1,this.callbackNode=this.pendingContext=this.context=null,this.callbackPriority=0,this.eventTimes=Ul(0),this.expirationTimes=Ul(-1),this.entangledLanes=this.finishedLanes=this.mutableReadLanes=this.expiredLanes=this.pingedLanes=this.suspendedLanes=this.pendingLanes=0,this.entanglements=Ul(0),this.identifierPrefix=r,this.onRecoverableError=i,this.mutableSourceEagerHydrationData=null}function ma(e,t,n,r,i,l,a,u,d){return e=new qd(e,t,n,u,d),t===1?(t=1,l===!0&&(t|=8)):t=0,l=_t(3,null,null,t),e.current=l,l.stateNode=e,l.memoizedState={element:r,isDehydrated:n,cache:null,transitions:null,pendingSuspenseBoundaries:null},Eo(l),e}function Xd(e,t,n){var r=3<arguments.length&&arguments[3]!==void 0?arguments[3]:null;return{$$typeof:fe,key:r==null?null:""+r,children:e,containerInfo:t,implementation:n}}function Gu(e){if(!e)return xn;e=e._reactInternals;e:{if(Vt(e)!==e||e.tag!==1)throw Error(f(170));var t=e;do{switch(t.tag){case 3:t=t.stateNode.context;break e;case 1:if(at(t.type)){t=t.stateNode.__reactInternalMemoizedMergedChildContext;break e}}t=t.return}while(t!==null);throw Error(f(171))}if(e.tag===1){var n=e.type;if(at(n))return js(e,n,t)}return t}function qu(e,t,n,r,i,l,a,u,d){return e=ma(n,r,!0,e,i,l,a,u,d),e.context=Gu(null),n=e.current,r=rt(),i=zn(n),l=rn(r,i),l.callback=t??null,Sn(n,l,i),e.current.lanes=i,Lr(e,i,r),ct(e,r),e}function Nl(e,t,n,r){var i=t.current,l=rt(),a=zn(i);return n=Gu(n),t.context===null?t.context=n:t.pendingContext=n,t=rn(l,a),t.payload={element:e},r=r===void 0?null:r,r!==null&&(t.callback=r),e=Sn(i,t,a),e!==null&&(At(e,i,a,l),tl(e,i,a)),a}function Cl(e){if(e=e.current,!e.child)return null;switch(e.child.tag){case 5:return e.child.stateNode;default:return e.child.stateNode}}function Xu(e,t){if(e=e.memoizedState,e!==null&&e.dehydrated!==null){var n=e.retryLane;e.retryLane=n!==0&&n<t?n:t}}function ha(e,t){Xu(e,t),(e=e.alternate)&&Xu(e,t)}function Zd(){return null}var Zu=typeof reportError=="function"?reportError:function(e){console.error(e)};function ga(e){this._internalRoot=e}zl.prototype.render=ga.prototype.render=function(e){var t=this._internalRoot;if(t===null)throw Error(f(409));Nl(e,t,null,null)},zl.prototype.unmount=ga.prototype.unmount=function(){var e=this._internalRoot;if(e!==null){this._internalRoot=null;var t=e.containerInfo;Hn(function(){Nl(null,e,null,null)}),t[Zt]=null}};function zl(e){this._internalRoot=e}zl.prototype.unstable_scheduleHydration=function(e){if(e){var t=Ra();e={blockedOn:null,target:e,priority:t};for(var n=0;n<mn.length&&t!==0&&t<mn[n].priority;n++);mn.splice(n,0,e),n===0&&Aa(e)}};function va(e){return!(!e||e.nodeType!==1&&e.nodeType!==9&&e.nodeType!==11)}function El(e){return!(!e||e.nodeType!==1&&e.nodeType!==9&&e.nodeType!==11&&(e.nodeType!==8||e.nodeValue!==" react-mount-point-unstable "))}function Ju(){}function Jd(e,t,n,r,i){if(i){if(typeof r=="function"){var l=r;r=function(){var y=Cl(a);l.call(y)}}var a=qu(t,r,e,0,null,!1,!1,"",Ju);return e._reactRootContainer=a,e[Zt]=a.current,Qr(e.nodeType===8?e.parentNode:e),Hn(),a}for(;i=e.lastChild;)e.removeChild(i);if(typeof r=="function"){var u=r;r=function(){var y=Cl(d);u.call(y)}}var d=ma(e,0,!1,null,null,!1,!1,"",Ju);return e._reactRootContainer=d,e[Zt]=d.current,Qr(e.nodeType===8?e.parentNode:e),Hn(function(){Nl(t,d,n,r)}),d}function _l(e,t,n,r,i){var l=n._reactRootContainer;if(l){var a=l;if(typeof i=="function"){var u=i;i=function(){var d=Cl(a);u.call(d)}}Nl(t,a,e,i)}else a=Jd(n,t,e,i,r);return Cl(a)}Ta=function(e){switch(e.tag){case 3:var t=e.stateNode;if(t.current.memoizedState.isDehydrated){var n=Pr(t.pendingLanes);n!==0&&(Bl(t,n|1),ct(t,z()),(ce&6)===0&&(kr=z()+500,wn()))}break;case 13:Hn(function(){var r=nn(e,1);if(r!==null){var i=rt();At(r,e,1,i)}}),ha(e,1)}},Vl=function(e){if(e.tag===13){var t=nn(e,134217728);if(t!==null){var n=rt();At(t,e,134217728,n)}ha(e,134217728)}},Fa=function(e){if(e.tag===13){var t=zn(e),n=nn(e,t);if(n!==null){var r=rt();At(n,e,t,r)}ha(e,t)}},Ra=function(){return ge},Ia=function(e,t){var n=ge;try{return ge=e,t()}finally{ge=n}},Cr=function(e,t,n){switch(t){case"input":if(yt(e,n),t=n.name,n.type==="radio"&&t!=null){for(n=e;n.parentNode;)n=n.parentNode;for(n=n.querySelectorAll("input[name="+JSON.stringify(""+t)+'][type="radio"]'),t=0;t<n.length;t++){var r=n[t];if(r!==e&&r.form===e.form){var i=$i(r);if(!i)throw Error(f(90));Ln(r),yt(r,i)}}}break;case"textarea":Xn(e,n);break;case"select":t=n.value,t!=null&&ft(e,!!n.multiple,t,!1)}},yi=sa,xi=Hn;var ef={usingClientEntryPoint:!1,Events:[Kr,sr,$i,qt,wt,sa]},ai={findFiberByHostInstance:An,bundleType:0,version:"18.3.1",rendererPackageName:"react-dom"},tf={bundleType:ai.bundleType,version:ai.version,rendererPackageName:ai.rendererPackageName,rendererConfig:ai.rendererConfig,overrideHookState:null,overrideHookStateDeletePath:null,overrideHookStateRenamePath:null,overrideProps:null,overridePropsDeletePath:null,overridePropsRenamePath:null,setErrorHandler:null,setSuspenseHandler:null,scheduleUpdate:null,currentDispatcherRef:de.ReactCurrentDispatcher,findHostInstanceByFiber:function(e){return e=_r(e),e===null?null:e.stateNode},findFiberByHostInstance:ai.findFiberByHostInstance||Zd,findHostInstancesForRefresh:null,scheduleRefresh:null,scheduleRoot:null,setRefreshHandler:null,getCurrentFiber:null,reconcilerVersion:"18.3.1-next-f1338f8080-20240426"};if(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__<"u"){var Pl=__REACT_DEVTOOLS_GLOBAL_HOOK__;if(!Pl.isDisabled&&Pl.supportsFiber)try{cn=Pl.inject(tf),bt=Pl}catch{}}return dt.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED=ef,dt.createPortal=function(e,t){var n=2<arguments.length&&arguments[2]!==void 0?arguments[2]:null;if(!va(t))throw Error(f(200));return Xd(e,t,null,n)},dt.createRoot=function(e,t){if(!va(e))throw Error(f(299));var n=!1,r="",i=Zu;return t!=null&&(t.unstable_strictMode===!0&&(n=!0),t.identifierPrefix!==void 0&&(r=t.identifierPrefix),t.onRecoverableError!==void 0&&(i=t.onRecoverableError)),t=ma(e,1,!1,null,null,n,!1,r,i),e[Zt]=t.current,Qr(e.nodeType===8?e.parentNode:e),new ga(t)},dt.findDOMNode=function(e){if(e==null)return null;if(e.nodeType===1)return e;var t=e._reactInternals;if(t===void 0)throw typeof e.render=="function"?Error(f(188)):(e=Object.keys(e).join(","),Error(f(268,e)));return e=_r(t),e=e===null?null:e.stateNode,e},dt.flushSync=function(e){return Hn(e)},dt.hydrate=function(e,t,n){if(!El(t))throw Error(f(200));return _l(null,e,t,!0,n)},dt.hydrateRoot=function(e,t,n){if(!va(e))throw Error(f(405));var r=n!=null&&n.hydratedSources||null,i=!1,l="",a=Zu;if(n!=null&&(n.unstable_strictMode===!0&&(i=!0),n.identifierPrefix!==void 0&&(l=n.identifierPrefix),n.onRecoverableError!==void 0&&(a=n.onRecoverableError)),t=qu(t,null,e,1,n??null,i,!1,l,a),e[Zt]=t.current,Qr(e),r)for(e=0;e<r.length;e++)n=r[e],i=n._getVersion,i=i(n._source),t.mutableSourceEagerHydrationData==null?t.mutableSourceEagerHydrationData=[n,i]:t.mutableSourceEagerHydrationData.push(n,i);return new zl(t)},dt.render=function(e,t,n){if(!El(t))throw Error(f(200));return _l(null,e,t,!1,n)},dt.unmountComponentAtNode=function(e){if(!El(e))throw Error(f(40));return e._reactRootContainer?(Hn(function(){_l(null,null,e,!1,function(){e._reactRootContainer=null,e[Zt]=null})}),!0):!1},dt.unstable_batchedUpdates=sa,dt.unstable_renderSubtreeIntoContainer=function(e,t,n,r){if(!El(n))throw Error(f(200));if(e==null||e._reactInternals===void 0)throw Error(f(38));return _l(e,t,n,!1,r)},dt.version="18.3.1-next-f1338f8080-20240426",dt}var ac;function df(){if(ac)return wa.exports;ac=1;function s(){if(!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__>"u"||typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE!="function"))try{__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(s)}catch(h){console.error(h)}}return s(),wa.exports=cf(),wa.exports}var sc;function ff(){if(sc)return Ll;sc=1;var s=df();return Ll.createRoot=s.createRoot,Ll.hydrateRoot=s.hydrateRoot,Ll}var pf=ff();const mf=dc(pf),hf="modulepreload",gf=function(s,h){return new URL(s,h).href},uc={},vf=function(h,f,w){let x=Promise.resolve();if(f&&f.length>0){let L=function(X){return Promise.all(X.map(K=>Promise.resolve(K).then(ee=>({status:"fulfilled",value:ee}),ee=>({status:"rejected",reason:ee}))))};const O=document.getElementsByTagName("link"),U=document.querySelector("meta[property=csp-nonce]"),le=(U==null?void 0:U.nonce)||(U==null?void 0:U.getAttribute("nonce"));x=L(f.map(X=>{if(X=gf(X,w),X in uc)return;uc[X]=!0;const K=X.endsWith(".css"),ee=K?'[rel="stylesheet"]':"";if(!!w)for(let te=O.length-1;te>=0;te--){const H=O[te];if(H.href===X&&(!K||H.rel==="stylesheet"))return}else if(document.querySelector(`link[href="${X}"]${ee}`))return;const ne=document.createElement("link");if(ne.rel=K?"stylesheet":hf,K||(ne.as="script"),ne.crossOrigin="",ne.href=X,le&&ne.setAttribute("nonce",le),document.head.appendChild(ne),K)return new Promise((te,H)=>{ne.addEventListener("load",te),ne.addEventListener("error",()=>H(new Error(`Unable to preload CSS for ${X}`)))})}))}function E(L){const O=new Event("vite:preloadError",{cancelable:!0});if(O.payload=L,window.dispatchEvent(O),!O.defaultPrevented)throw L}return x.then(L=>{for(const O of L||[])O.status==="rejected"&&E(O.reason);return h().catch(E)})},yf=[" in provincia","mercato settimanale a ","fiere, mostre e mercati"," http://"," https://"," il mercato settimanale di "],xf=new Set(["AL","BS","MI","BG","BO","FI","RM","NA"]);function fc(s){const h=String(s||"").trim(),f=h.toLocaleLowerCase("it");return h.length>68||h.startsWith('"')||h.startsWith("“")||h.startsWith("”")||xf.has(h.toUpperCase())||yf.some(w=>f.includes(w))||/^(via|viale|corso)\s/i.test(h)&&h.includes("-")}function wf(s){return fc(s)?"Località da verificare":String(s||"")}const kf="La località riportata dalla fonte non identifica con sicurezza un Comune. Controlla la fonte originale prima di spostarti.",Sf="./",jf=1800*1e3;let Dl=0,ui=null;const pc="mercati_preferiti";let fi;const pi=new Map;function Nf(s){if(typeof s!="string"||!/^data\/v1\/[a-zA-Z0-9._/-]+\.json$/.test(s)||s.includes(".."))throw new Error("Percorso catalogo non valido");return Sf.replace(/\/$/,"/")+s}async function mi(s,h=!1,f=!1){const w=await fetch(Nf(s),{cache:h?"force-cache":f?"no-cache":"default"});if(!w.ok)throw new Error("Catalogo non disponibile: "+s+" ("+w.status+")");return w.json()}async function Cf(s,h,f){let w=0;const x=new Array(s.length);return await Promise.all(Array.from({length:Math.min(s.length,h)},async()=>{for(;w<s.length;){const E=w++;x[E]=await f(s[E],E)}})),x}async function mc(s){if(s.schema!==1||!Number.isInteger(s.total)||s.total<0)throw new Error("Manifest del catalogo non valido");if(s.index){const E=await mi(s.index,!0);if(E.schema!==1||!Array.isArray(E.markets)||E.markets.length!==s.total)throw new Error("Indice mercati incompleto");const L=["slug","nome","citta","regione","categoria","tags","lat","lng","position_quality","orario_testo","date_quality","date"],O=E.markets.map(le=>{if(!Array.isArray(le))return le;if(le.length!==L.length)throw new Error("Formato indice errato");return Object.fromEntries(L.map((X,K)=>[X,le[K]]))}),U=new Set;for(const le of O){if(!le.slug||U.has(le.slug))throw new Error("Indice duplicato o non valido");U.add(le.slug)}return{manifest:s,markets:O}}let h;if(s.layout==="single")h=[{path:s.catalog}];else if(s.layout==="regional"&&Array.isArray(s.regions))h=s.regions;else throw new Error("Formato catalogo non supportato");const w=(await Cf(h,4,async E=>{const L=await mi(E.path,!0);if(L.schema!==1||!Array.isArray(L.markets))throw new Error("File mercati non valido: "+E.path);if(E.count!==void 0&&L.markets.length!==E.count)throw new Error("Conteggio non valido: "+E.path);return L.markets})).flat();if(w.length!==s.total)throw new Error("Catalogo incompleto");const x=new Set;for(const E of w){if(!E.slug||x.has(E.slug))throw new Error("ID mercato duplicato o assente");x.add(E.slug)}return{manifest:s,markets:w}}async function zf(){const s=await mc(await mi("data/v1/manifest.json"));return Dl=Date.now(),s}function Ef(s,h=Date.now()){return Number.isFinite(h)&&(!s||h>=s&&h-s>=jf)}async function _f(s=Date.now()){const h=await Pa();if(ui)return ui;if(!Ef(Dl,s))return!1;ui=(async()=>{const f=await mi("data/v1/manifest.json",!1,!0);if(f.content_signature&&h.manifest.content_signature&&f.content_signature===h.manifest.content_signature&&f.index===h.manifest.index)return Dl=s,!1;const w=await mc(f);return fi=Promise.resolve(w),pi.clear(),Dl=s,!0})();try{return await ui}finally{ui=null}}async function Pa(){return fi||(fi=zf().catch(s=>{throw fi=null,s})),fi}function Pf(s=new Date){return[s.getFullYear(),String(s.getMonth()+1).padStart(2,"0"),String(s.getDate()).padStart(2,"0")].join("-")}function Lf(s=[]){const h=Pf();return(s||[]).filter(f=>typeof f=="string"&&f>=h).sort()[0]||null}function Df(s,h,f,w){if(![s,h,f,w].every(Number.isFinite))return 1/0;const x=Math.PI/180,E=(f-s)*x,L=(w-h)*x,O=Math.sin(E/2)**2+Math.cos(s*x)*Math.cos(f*x)*Math.sin(L/2)**2;return 6371*2*Math.atan2(Math.sqrt(O),Math.sqrt(1-O))}function Ca(s,h,f){const w=typeof s.lat=="number"&&Number.isFinite(s.lat)?s.lat:null,x=typeof s.lng=="number"&&Number.isFinite(s.lng)?s.lng:null;return{id:s.slug,nome:s.nome||"",citta:s.citta||"",provincia:s.provincia||"",regione:s.regione||"",indirizzo:s.indirizzo||"",lat:w,lng:x,categoria:s.categoria||"misto",tags:s.tags||[],orario_testo:s.orario_testo||"",ricorrenza_testo:s.ricorrenza_testo||"",descrizione:s.descrizione||"",date:s.date||[],prossima_data:Lf(s.date),confidence:s.confidence??0,completezza:s.completezza??0,verificato_il:s.verificato_il||"",aggiornato_il:s.aggiornato_il||"",aggiornamento_ambito:s.aggiornamento_ambito||"",date_quality:s.date_quality||"prevista",position_quality:s.position_quality||"sconosciuta",status:s.status||"non_confermato",fonte:s.fonte||"",url_fonte:s.url_fonte||"",navigazione_sospesa_motivo:s.navigazione_sospesa_motivo||"",coordinate_sospese_motivo:s.coordinate_sospese_motivo||"",fonti:Array.isArray(s.fonti)?s.fonti.filter(E=>E&&typeof E.nome=="string"&&typeof E.url=="string"):[],distance:Number.isFinite(h)&&Number.isFinite(f)&&Number.isFinite(w)&&Number.isFinite(x)?Df(h,f,w,x):null}}async function Mf({userLat:s=null,userLng:h=null}={}){const{markets:f}=await Pa();return f.map(w=>Ca(w,s,h))}async function Tf(s){const{manifest:h,markets:f}=await Pa(),w=f.find(O=>O.slug===s);if(!w)return null;if(!h.index)return Ca(w,null,null);const x=h.layout==="single"?{path:h.catalog}:h.regions.find(O=>O.name===w.regione);if(!x)throw new Error("Dettagli non disponibili per la regione");if(!pi.has(x.path)){const O=mi(x.path,!0).then(U=>{if(U.schema!==1||!Array.isArray(U.markets))throw new Error("Dati regionali non validi");if(x.count!==void 0&&U.markets.length!==x.count)throw new Error("Catalogo regionale incompleto");return U.markets}).catch(U=>{throw pi.delete(x.path),U});pi.set(x.path,O)}const L=(await pi.get(x.path)).find(O=>O.slug===s);if(!L)throw new Error("Mercato non trovato nel file regionale");return Ca(L,null,null)}function Ff(){return"static"}function hc(){try{return new Set(JSON.parse(localStorage.getItem(pc)||"[]"))}catch{return new Set}}async function Rf(){return hc()}async function If(s){const h=hc();h.has(s)?h.delete(s):h.add(s);try{localStorage.setItem(pc,JSON.stringify([...h]))}catch{}return h}const Of={alimentare:"Alimentare",antiquariato:"Antiquariato",vintage_abbigliamento:"Vintage e abbigliamento",usato:"Usato",artigianato:"Artigianato",misto:"Misto"},Af={Alimentare:"🍅",Antiquariato:"🏺","Vintage e abbigliamento":"👗",Usato:"📦",Artigianato:"🎨",Misto:"🎪"},Uf={Alimentare:"#446E47",Antiquariato:"#B94439","Vintage e abbigliamento":"#705073",Usato:"#805B08",Artigianato:"#216886",Misto:"#9C4B36"};function cc(s,h,f){const w=Of[s.categoria]||s.categoria||"Misto",x=fc(s.citta)||s.navigazione_sospesa_motivo==="indirizzo_e_punto_sorgente_non_riconciliati";return{id:s.id,name:s.nome,city:wf(s.citta),originalCity:s.citta,locationReviewRequired:x,region:s.regione,address:s.indirizzo||"",lat:s.lat,lng:s.lng,category:w,tags:s.tags||[],dates:s.date||[],hours:s.orario_testo||"",recurrence:s.ricorrenza_testo||"",description:s.descrizione||"",source:s.fonte||"",confidence:s.confidence??0,dataCompleteness:s.completezza??0,sourceUpdated:s.aggiornato_il?s.aggiornato_il.slice(0,10):"",sourceUpdateScope:s.aggiornamento_ambito||"",lastVerified:s.verificato_il?s.verificato_il.slice(0,10):"",dateQuality:s.date_quality||"prevista",positionQuality:s.position_quality||"sconosciuta",status:s.status||"non_confermato",sourceUrl:s.url_fonte||"",sourceEvidence:Array.isArray(s.fonti)?s.fonti.filter(E=>E&&E.url&&E.nome):[],distance:Number.isFinite(s.distance)?s.distance:null}}function Bf(){const[s,h]=T.useState([]),[f,w]=T.useState(!0),[x,E]=T.useState(0),L=null,[O,U]=T.useState(null),[le,X]=T.useState(new Set),[K,ee]=T.useState({regioni:[],citta:[]}),[ve,ne]=T.useState(null),[te,H]=T.useState("idle"),[Fe,we]=T.useState(""),Ne=(ve==null?void 0:ve.lat)??null,de=(ve==null?void 0:ve.lng)??null,Me=Ff(),fe=T.useCallback(()=>{if(typeof navigator>"u"||!navigator.geolocation){H("unavailable"),we("La posizione non è disponibile su questo dispositivo.");return}H("requesting"),we(""),navigator.geolocation.getCurrentPosition(D=>{var se,G;const Z=(se=D==null?void 0:D.coords)==null?void 0:se.latitude,ae=(G=D==null?void 0:D.coords)==null?void 0:G.longitude;if(!Number.isFinite(Z)||!Number.isFinite(ae)){H("error"),we("Non sono riuscito a leggere la posizione.");return}ne({lat:Z,lng:ae}),H("ready"),we("")},D=>{H((D==null?void 0:D.code)===1?"denied":"error"),we((D==null?void 0:D.code)===1?"Accesso alla posizione negato. Puoi cercare per città.":"Posizione non disponibile. Puoi cercare per città.")},{enableHighAccuracy:!1,timeout:12e3,maximumAge:3e5})},[]),ke=T.useCallback(()=>{ne(null),H("idle"),we("")},[]);T.useEffect(()=>{let D=!0;const Z=()=>{document.visibilityState!=="hidden"&&_f().then(se=>{D&&se&&E(G=>G+1)}).catch(()=>{})};document.addEventListener("visibilitychange",Z),window.addEventListener("focus",Z);const ae=window.setInterval(Z,1800*1e3);return()=>{D=!1,document.removeEventListener("visibilitychange",Z),window.removeEventListener("focus",Z),window.clearInterval(ae)}},[]),T.useEffect(()=>{let D=!1;async function Z(){try{w(!0);const[ae,se]=await Promise.all([Mf({userLat:Ne,userLng:de}),Rf()]),G=ae.map(B=>cc(B,Ne,de)),P={regioni:[...new Set(G.map(B=>B.region).filter(Boolean))].sort(),citta:[...new Set(G.filter(B=>!B.locationReviewRequired).map(B=>B.city).filter(Boolean))].sort()};if(D)return;h(G),X(se),ee(P),U(null)}catch(ae){D||U(ae.message)}finally{D||w(!1)}}return Z(),()=>{D=!0}},[Ne,de,x]);const Ue=T.useCallback(async D=>{X(Z=>{const ae=new Set(Z);return ae.has(D)?ae.delete(D):ae.add(D),ae});try{const Z=await If(D);X(Z)}catch{}},[]),Ke=T.useCallback(async D=>{const Z=await Tf(D);return Z?cc(Z):null},[Ne,de]),Ye=T.useMemo(()=>["Alimentare","Antiquariato","Vintage e abbigliamento","Usato","Artigianato","Misto"],[]),$=T.useMemo(()=>K.regioni.length>0?K.regioni:[...new Set(s.map(D=>D.region))].sort(),[K.regioni,s]),ye=T.useMemo(()=>K.citta.length>0?K.citta:[...new Set(s.map(D=>D.city))].sort(),[K.citta,s]);return{markets:s,loading:f,error:O,seedStatus:L,favorites:le,toggleFav:Ue,getMarketDetails:Ke,categories:Ye,regions:$,cities:ye,categoryIcons:Af,categoryColors:Uf,dataMode:Me,userLat:Ne,userLng:de,positionStatus:te,positionError:Fe,requestPosition:fe,clearPosition:ke}}const gc=["Lun","Mar","Mer","Gio","Ven","Sab","Dom"];function He(s){return String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("it").replace(/[’']/g," ").replace(/[^a-z0-9]+/g," ").trim().replace(/\s+/g," ")}function vc(s){const h=He(s==null?void 0:s.name),f=He(s==null?void 0:s.city);if(!h||!f||!(s!=null&&s.region))return!1;const w=h.match(/^mercat(?:o|ino) settimanale (?:di|a|ad|del|della|dei|in|nel|nella) (.+)$/);return!!(w&&w[1]===f)}function Vf(s){return`weekly:${He(s.region)}:${He(s.city)}`}function hi(s){if(typeof s!="string"||!/^\d{4}-\d\d-\d\d$/.test(s))return null;const h=new Date(s+"T12:00:00");return Number.isNaN(h.getTime())||h.getFullYear()!==Number(s.slice(0,4))||h.getMonth()+1!==Number(s.slice(5,7))||h.getDate()!==Number(s.slice(8))?null:(h.getDay()+6)%7}function Tl(s=[],h=null,f=new Date){const w=[f.getFullYear(),String(f.getMonth()+1).padStart(2,"0"),String(f.getDate()).padStart(2,"0")].join("-");return s.filter(x=>x>=w&&(h===null||hi(x)===h)).sort()[0]||null}function bf(s,{keepSingleWeeklyGroups:h=!1}={}){const f=[],w=new Map;for(const x of s){if(!vc(x)){f.push({kind:"market",key:x.id,market:x});continue}const E=Vf(x);let L=w.get(E);L||(L={kind:"group",key:E,city:x.city,region:x.region,markets:[]},w.set(E,L),f.push(L)),L.markets.push(x)}return f.flatMap(x=>x.kind==="group"&&x.markets.length===1&&!h?[{kind:"market",key:x.markets[0].id,market:x.markets[0]}]:[x])}function Wf(s,h,f="",w=""){if(h===null)return!1;const x=He(s.city);return!!f&&x===He(f)||!!w.trim()&&x===He(w.trim())}function Qf(s,h){if(!s||!h||s.id===h.id||![s,h].every(vc)||[s,h].some(H=>/^(lo-mercap-|bo-open-|pg-corciano-)/.test(H.id||""))||He(s.region)!==He(h.region)||He(s.city)!==He(h.city)||He(s.category)!==He(h.category))return!1;const f=za(s.address),w=za(h.address);if(!f||f!==w||!s.sourceUrl||s.sourceUrl!==h.sourceUrl||!/^https:\/\//i.test(s.sourceUrl)||s.dateQuality!=="prevista"||h.dateQuality!=="prevista"||s.lastVerified||h.lastVerified||(s.status||"non_confermato")!==(h.status||"non_confermato"))return!1;const x=He(s.hours),E=He(h.hours);if(x&&E&&x!==E)return!1;const L=[...new Set(s.dates||[])].sort(),O=[...new Set(h.dates||[])].sort();if(L.length<2||O.length<2||L[0]!==O[0]||L[1]!==O[1])return!1;const U=hi(L[0]);if(U===null||U!==hi(L[1]))return!1;const[le,X,K]=L[0].split("-").map(Number),[ee,ve,ne]=L[1].split("-").map(Number);if(Date.UTC(ee,ve-1,ne)-Date.UTC(le,X-1,K)!==6048e5||![s,h].every(H=>{const Fe=He(H.recurrence);return Fe.includes("settimanale")&&!/mensil|quindicinal|alternat/.test(Fe)}))return!1;if([s.lat,s.lng,h.lat,h.lng].every(Number.isFinite)){const Fe=111.2*Math.cos((s.lat+h.lat)/2*Math.PI/180);if(Math.hypot((s.lat-h.lat)*111.2,(s.lng-h.lng)*Fe)>.25)return!1}return!0}function $f(s){return[...s].sort((h,f)=>{const w=x=>{var E;return+!!x.hours*8+ +!!x.description*3+ +!!((E=x.sourceEvidence)!=null&&E.length)*2+(Number(x.dataCompleteness)||0)/100};return w(f)-w(h)||String(f.sourceUpdated||"").localeCompare(String(h.sourceUpdated||""))||String(h.id).localeCompare(String(f.id))})[0]}function Hf(s=[]){const h=[];for(const f of s){const w=h.find(x=>x.records.every(E=>Qf(E,f)));w?w.records.push(f):h.push({records:[f]})}return h.map(f=>{const w=$f(f.records);return{key:w.id,market:w,records:[...f.records].sort((x,E)=>String(x.id).localeCompare(String(E.id)))}})}function Kf(s){const h=new Set;for(const f of s)for(const w of f.dates||[]){const x=hi(w);x!==null&&h.add(x)}return[...h].sort((f,w)=>f-w)}function za(s){const h=String(s||"").trim(),f=He(h);return!f||f.length<7||["centro","centro storico","da definire","non disponibile","sconosciuto","non verificato","sede da verificare","citta","varie sedi"].includes(f)?"":f}function Yf(s,h){return s.positionQuality!=="precisa"||h.positionQuality!=="precisa"||![s.lat,s.lng,h.lat,h.lng].every(Number.isFinite)?!1:Math.abs(s.lat-h.lat)>.0025||Math.abs(s.lng-h.lng)>.0025}function Gf(s){const h=[],f=new Map;for(const w of s){const x=za(w.address);let E=null;if(x){for(const L of f.get(x)||[])if(!Yf(L.markets[0],w)){E=L;break}}E||(E={key:x?`venue:${x}:${w.id}`:`unknown:${w.id}`,address:x?w.address.trim():"",verifiedAddress:!!x,markets:[]},h.push(E),x&&(f.has(x)||f.set(x,[]),f.get(x).push(E))),E.markets.push(w)}return h.sort((w,x)=>{const E=w.markets.map(O=>Tl(O.dates)).filter(Boolean).sort()[0]||"9999",L=x.markets.map(O=>Tl(O.dates)).filter(Boolean).sort()[0]||"9999";return E.localeCompare(L)||w.address.localeCompare(x.address,"it")})}function qf(s=new Date){const h=s.getFullYear(),f=String(s.getMonth()+1).padStart(2,"0"),w=String(s.getDate()).padStart(2,"0");return[h,f,w].join("-")}function Xf(s,h=new Date){const f=qf(h);return Array.isArray(s)&&s.some(w=>typeof w=="string"&&/^\d{4}-\d{2}-\d{2}$/.test(w)&&w>=f)}function Ea(s,h,f=new Date){return Xf(s,f)?h==="confermata"?"":"Date previste, non confermate per ogni singola edizione. Controlla la fonte prima di partire.":"Nessuna data futura disponibile. Giorni e aperture da verificare presso la fonte prima di partire."}function ja(s){return s?new Date(s+"T12:00:00").toLocaleDateString("it-IT",{weekday:"short",day:"numeric",month:"short"}):"Data da verificare"}function Zf({group:s,loadMarket:h,onOpenMarket:f,selectedWeekday:w=null,autoExpand:x=!1}){const E=T.useId(),[L,O]=T.useState(x),[U,le]=T.useState({}),[X,K]=T.useState(!1),[ee,ve]=T.useState(""),[ne,te]=T.useState(!1),[H,Fe]=T.useState({}),we=s.markets.map($=>$.id).join("|");T.useEffect(()=>{x&&O(!0)},[x]),T.useEffect(()=>{if(!L)return;const $=s.markets.filter(D=>!U[D.id]);if(!$.length)return;let ye=!1;return K(!0),ve(""),Promise.allSettled($.map(D=>h(D.id))).then(D=>{if(ye)return;const Z={};let ae=0;D.forEach((se,G)=>{se.status==="fulfilled"&&se.value?Z[$[G].id]=se.value:(Z[$[G].id]=$[G],ae++)}),le(se=>({...se,...Z})),ae&&ve("Alcune sedi non sono disponibili nei dettagli: riprova più tardi."),K(!1)}),()=>{ye=!0}},[L,we,h]);const Ne=T.useMemo(()=>Kf(s.markets),[s.markets]),de=T.useMemo(()=>s.markets.map($=>Tl($.dates||[],w)).filter(Boolean).sort()[0]||null,[s.markets,w]),Me=T.useMemo(()=>L?Gf(s.markets.map($=>U[$.id]||$)):[],[s.markets,U,L]),fe=Me.filter($=>$.verifiedAddress),ke=Me.filter($=>!$.verifiedAddress),Ue=[...fe,...ne||fe.length===0?ke:[]],Ke=s.markets.some($=>$.dateQuality!=="confermata"),Ye=Ea(s.markets.flatMap($=>$.dates||[]),Ke?"prevista":"confermata");return o.jsxs("article",{className:"weekly-city-card","data-testid":"weekly-city-group","aria-label":`Mercati settimanali a ${s.city}`,children:[o.jsxs("div",{className:"weekly-city-top",children:[o.jsxs("span",{className:"weekly-city-overline",children:["Mercati settimanali · ",s.city]}),o.jsxs("span",{className:"weekly-city-counter",children:[s.markets.length," schede"]})]}),o.jsxs("h2",{className:"weekly-city-heading",children:["Mercati settimanali a ",s.city]}),o.jsxs("div",{className:"weekly-city-subtitle",children:[o.jsx("span",{children:Ne.length?`${Ne.length} ${Ne.length===1?"giornata":"giornate"} della settimana`:"Calendario da verificare"}),de&&o.jsxs("span",{children:["Prossimo: ",ja(de)]})]}),o.jsx("div",{className:"weekly-day-chips","aria-label":"Giorni registrati",children:Ne.map($=>o.jsx("span",{className:w===$?"weekly-day-chip highlighted":"weekly-day-chip",children:gc[$]},$))}),Ye&&o.jsx("p",{className:"weekly-city-caution",children:Ye}),o.jsxs("button",{type:"button",className:"weekly-city-toggle","aria-controls":E,"aria-expanded":L,onClick:()=>O($=>!$),children:[o.jsx("span",{children:L?"Nascondi sedi e giornate":"Visualizza sedi e giornate"}),o.jsx("span",{"aria-hidden":"true",className:L?"weekly-chevron open":"weekly-chevron",children:"⌄"})]}),L&&o.jsxs("div",{id:E,className:"weekly-city-panel",children:[X&&o.jsx("div",{className:"weekly-load",role:"status",children:"Caricamento sedi…"}),ee&&o.jsx("p",{className:"weekly-city-caution",role:"alert",children:ee}),!X&&Me.length>0&&o.jsxs(o.Fragment,{children:[o.jsxs("p",{className:"weekly-venue-total",children:[fe.length," ",fe.length===1?"sede riportata":"sedi riportate",ke.length>0&&` · ${ke.length} ${ke.length===1?"scheda":"schede"} senza indirizzo`,". Ogni scheda e fonte resta accessibile. Le segnalazioni identiche sono raggruppate solo nella visualizzazione."]}),ke.length>0&&fe.length>0&&o.jsxs("button",{type:"button",className:"weekly-unknown-toggle","aria-expanded":ne,onClick:()=>te($=>!$),children:[ne?"Nascondi":"Mostra",` ${ke.length} ${ke.length===1?"appuntamento":"appuntamenti"} senza sede identificata`]}),Ue.map(($,ye)=>o.jsxs("section",{className:"weekly-venue","data-known":$.verifiedAddress?"true":"false","aria-label":$.address||"Sede da verificare",children:[o.jsxs("div",{className:"weekly-venue-title-row",children:[o.jsx("span",{className:"weekly-venue-index",children:ye+1}),o.jsxs("div",{children:[o.jsx("h3",{className:"weekly-venue-title",children:$.address||"Sede da verificare"}),!$.verifiedAddress&&o.jsx("p",{className:"weekly-venue-note",children:"Indirizzo assente o troppo generico: non unito ad altre sedi"})]})]}),o.jsx("div",{className:"weekly-appointment-list",children:Hf($.markets).map(D=>{const Z=D.market,ae=Tl(Z.dates||[],w),se=!!H[D.key];return o.jsxs("div",{className:"weekly-appointment-group",children:[o.jsxs("button",{type:"button",className:"weekly-appointment",onClick:()=>f(Z),"aria-label":"Apri "+ja(ae)+", "+($.address||s.city),children:[o.jsx("span",{className:"weekly-appointment-date",children:ja(ae)}),o.jsxs("span",{className:"weekly-appointment-meta",children:[Z.hours||"Orario da verificare",Z.dateQuality!=="confermata"&&o.jsx("small",{children:" · Previsto"})]}),o.jsx("span",{"aria-hidden":"true",className:"weekly-appointment-arrow",children:"›"})]}),D.records.length>1&&o.jsxs(o.Fragment,{children:[o.jsxs("button",{type:"button",className:"weekly-duplicate-toggle","aria-expanded":se,onClick:()=>Fe(G=>({...G,[D.key]:!G[D.key]})),children:[D.records.length," schede della stessa fonte"," · ",se?"Nascondi originali":"Mostra originali"]}),se&&o.jsx("div",{className:"weekly-duplicate-records",children:D.records.map(G=>o.jsxs("button",{type:"button",className:"weekly-original-record",onClick:()=>f(G),children:[G.name," · ",G.hours||"Orario da verificare",o.jsx("span",{"aria-hidden":"true",children:"›"})]},G.id))})]})]},D.key)})})]},$.key))]})]})]})}function Jf(s,h="",f=!1){return typeof h=="string"&&h.trim()&&!f?null:s||null}const ep=T.lazy(()=>vf(()=>import("./MarketsMap-B15qIIIi.js"),__vite__mapDeps([0,1]),import.meta.url)),tp=["Alimentare","Antiquariato","Vintage e abbigliamento","Usato","Artigianato","Misto"],np=[],rp=[],ip={Alimentare:"🍅",Antiquariato:"🏺","Vintage e abbigliamento":"👗",Usato:"📦",Artigianato:"🎨",Misto:"🎪"},lp={Alimentare:"#446E47",Antiquariato:"#B94439","Vintage e abbigliamento":"#705073",Usato:"#805B08",Artigianato:"#216886",Misto:"#9C4B36"};function an(s=new Date){return[s.getFullYear(),String(s.getMonth()+1).padStart(2,"0"),String(s.getDate()).padStart(2,"0")].join("-")}const Ml=new Date,ci=an(Ml);function Na(s){if(!s)return"Data da verificare";const h=new Date(s+"T00:00:00");return Number.isNaN(h.getTime())?"Data da verificare":h.toLocaleDateString("it-IT",{weekday:"short",day:"numeric",month:"short"})}function op(s=[],h="prevista"){const f=h==="confermata",w=f?"":" · da verificare",x=new Date,E=an(x),L=new Date(x);L.setDate(L.getDate()+1);const O=new Date(x);O.setDate(O.getDate()+(6-x.getDay()+7)%7);const U=new Date(O);return U.setDate(U.getDate()+1),s.includes(E)?{label:"Oggi"+w,color:f?"#B94439":"#81796D"}:s.includes(an(L))?{label:"Domani"+w,color:f?"#B94439":"#81796D"}:s.includes(an(O))||s.includes(an(U))?{label:"Weekend"+w,color:f?"#446E47":"#81796D"}:null}function di(s=[]){return s.filter(h=>h>=an()).sort()[0]||null}const je=({name:s,size:h=20,color:f="currentColor",strokeWidth:w=1.8})=>{const x={search:o.jsxs(o.Fragment,{children:[o.jsx("circle",{cx:"11",cy:"11",r:"8"}),o.jsx("line",{x1:"21",y1:"21",x2:"16.65",y2:"16.65"})]}),filter:o.jsx(o.Fragment,{children:o.jsx("polygon",{points:"22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"})}),heart:o.jsx("path",{d:"M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"}),heartFilled:o.jsx("path",{d:"M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z",fill:"currentColor"}),mapPin:o.jsxs(o.Fragment,{children:[o.jsx("path",{d:"M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"}),o.jsx("circle",{cx:"12",cy:"10",r:"3"})]}),clock:o.jsxs(o.Fragment,{children:[o.jsx("circle",{cx:"12",cy:"12",r:"10"}),o.jsx("polyline",{points:"12 6 12 12 16 14"})]}),compass:o.jsxs(o.Fragment,{children:[o.jsx("circle",{cx:"12",cy:"12",r:"10"}),o.jsx("polygon",{points:"16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"})]}),bell:o.jsxs(o.Fragment,{children:[o.jsx("path",{d:"M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"}),o.jsx("path",{d:"M13.73 21a2 2 0 0 1-3.46 0"})]}),settings:o.jsxs(o.Fragment,{children:[o.jsx("circle",{cx:"12",cy:"12",r:"3"}),o.jsx("path",{d:"M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"})]}),chevronLeft:o.jsx("polyline",{points:"15 18 9 12 15 6"}),chevronRight:o.jsx("polyline",{points:"9 18 15 12 9 6"}),x:o.jsxs(o.Fragment,{children:[o.jsx("line",{x1:"18",y1:"6",x2:"6",y2:"18"}),o.jsx("line",{x1:"6",y1:"6",x2:"18",y2:"18"})]}),copy:o.jsxs(o.Fragment,{children:[o.jsx("rect",{x:"9",y:"9",width:"13",height:"13",rx:"2",ry:"2"}),o.jsx("path",{d:"M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"})]}),navigation:o.jsx("polygon",{points:"3 11 22 2 13 21 11 13 3 11"}),share:o.jsxs(o.Fragment,{children:[o.jsx("circle",{cx:"18",cy:"5",r:"3"}),o.jsx("circle",{cx:"6",cy:"12",r:"3"}),o.jsx("circle",{cx:"18",cy:"19",r:"3"}),o.jsx("line",{x1:"8.59",y1:"13.51",x2:"15.42",y2:"17.49"}),o.jsx("line",{x1:"15.41",y1:"6.51",x2:"8.59",y2:"10.49"})]}),calendar:o.jsxs(o.Fragment,{children:[o.jsx("rect",{x:"3",y:"4",width:"18",height:"18",rx:"2",ry:"2"}),o.jsx("line",{x1:"16",y1:"2",x2:"16",y2:"6"}),o.jsx("line",{x1:"8",y1:"2",x2:"8",y2:"6"}),o.jsx("line",{x1:"3",y1:"10",x2:"21",y2:"10"})]}),list:o.jsxs(o.Fragment,{children:[o.jsx("line",{x1:"8",y1:"6",x2:"21",y2:"6"}),o.jsx("line",{x1:"8",y1:"12",x2:"21",y2:"12"}),o.jsx("line",{x1:"8",y1:"18",x2:"21",y2:"18"}),o.jsx("line",{x1:"3",y1:"6",x2:"3.01",y2:"6"}),o.jsx("line",{x1:"3",y1:"12",x2:"3.01",y2:"12"}),o.jsx("line",{x1:"3",y1:"18",x2:"3.01",y2:"18"})]}),map:o.jsxs(o.Fragment,{children:[o.jsx("polygon",{points:"1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"}),o.jsx("line",{x1:"8",y1:"2",x2:"8",y2:"18"}),o.jsx("line",{x1:"16",y1:"6",x2:"16",y2:"22"})]}),check:o.jsx("polyline",{points:"20 6 9 17 4 12"}),minus:o.jsx("line",{x1:"5",y1:"12",x2:"19",y2:"12"}),plus:o.jsxs(o.Fragment,{children:[o.jsx("line",{x1:"12",y1:"5",x2:"12",y2:"19"}),o.jsx("line",{x1:"5",y1:"12",x2:"19",y2:"12"})]}),externalLink:o.jsxs(o.Fragment,{children:[o.jsx("path",{d:"M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"}),o.jsx("polyline",{points:"15 3 21 3 21 9"}),o.jsx("line",{x1:"10",y1:"14",x2:"21",y2:"3"})]}),info:o.jsxs(o.Fragment,{children:[o.jsx("circle",{cx:"12",cy:"12",r:"10"}),o.jsx("line",{x1:"12",y1:"16",x2:"12",y2:"12"}),o.jsx("line",{x1:"12",y1:"8",x2:"12.01",y2:"8"})]}),sort:o.jsxs(o.Fragment,{children:[o.jsx("line",{x1:"12",y1:"5",x2:"12",y2:"19"}),o.jsx("polyline",{points:"19 12 12 19 5 12"})]}),bookmark:o.jsx("path",{d:"M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"})};return o.jsx("svg",{width:h,height:h,viewBox:"0 0 24 24",fill:"none",stroke:f,strokeWidth:w,strokeLinecap:"round",strokeLinejoin:"round",style:{flexShrink:0},children:x[s]})},ap=`
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
`;function sp(){const{markets:s,loading:h,error:f,favorites:w,toggleFav:x,getMarketDetails:E,categories:L,regions:O,cities:U,categoryIcons:le,categoryColors:X,dataMode:K,userLat:ee,userLng:ve,positionStatus:ne,positionError:te,requestPosition:H,clearPosition:Fe}=Bf(),[we,Ne]=T.useState("esplora"),[de,Me]=T.useState("lista"),[fe,ke]=T.useState(""),[Ue,Ke]=T.useState("7giorni"),[Ye,$]=T.useState(!1),ye=Jf(Ue,fe,Ye),[D,Z]=T.useState(null),[ae,se]=T.useState(60),[G,P]=T.useState(!1),[B,F]=T.useState(!1),[m,k]=T.useState("data"),[q,J]=T.useState(null),[ie,oe]=T.useState(!1),[he,pe]=T.useState(""),[Se,Ge]=T.useState(null),[it,Ln]=T.useState([]),[Be,Pt]=T.useState(""),[qe,Lt]=T.useState(""),[yt,Kt]=T.useState(100),[xt,Dt]=T.useState(!1),[ft,lt]=T.useState(0),[qn,Xn]=T.useState([]),[sn,Zn]=T.useState(""),[Dn,Yt]=T.useState(""),[Mn,Gt]=T.useState(100),[pt,Tn]=T.useState("none"),[jr,gi]=T.useState(""),[La,vi]=T.useState(null);T.useRef(null);const Nr=L.length>0?L:tp,Fn=Object.keys(le).length>0?le:ip,Rn=Object.keys(X).length>0?X:lp,Cr=O.length>0?O:np,Ut=U.length>0?U:rp,xe=Number.isFinite(ee)&&Number.isFinite(ve),zr=T.useCallback((c,N)=>{N&&N.stopPropagation(),x(c)},[x]),qt=T.useCallback(async c=>{J(c),pe(""),oe(!0);try{const N=await E(c.id);J(z=>(z==null?void 0:z.id)===c.id?N||c:z)}catch(N){pe(N.message||"Impossibile caricare i dettagli")}finally{oe(!1)}},[E]),wt=T.useCallback(c=>{Ge(c),setTimeout(()=>Ge(null),2e3)},[]);T.useEffect(()=>{const c=()=>{const N=window.location.hash.replace(/^#/,""),z=new URLSearchParams(N).get("mercato"),b=z&&s.find(ue=>ue.id===z);b&&qt(b)};return c(),window.addEventListener("hashchange",c),()=>window.removeEventListener("hashchange",c)},[s,qt]);const yi=()=>{J(null),window.location.hash.startsWith("#mercato=")&&window.history.replaceState(null,"",window.location.pathname+window.location.search)},xi=async c=>{var b;const N=new URL(window.location.href);N.hash="mercato="+encodeURIComponent(c.id);const z={title:c.name,text:c.city,url:N.toString()};try{navigator.share?await navigator.share(z):(b=navigator.clipboard)!=null&&b.writeText?(await navigator.clipboard.writeText(z.url),wt("Link del mercato copiato.")):window.prompt("Copia questo link per condividerlo:",z.url)}catch(ue){(ue==null?void 0:ue.name)!=="AbortError"&&wt("Condivisione non riuscita.")}},Jn=c=>{var b;if(c.locationReviewRequired)return null;if(c.positionQuality==="precisa"&&Number.isFinite(c.lat)&&Number.isFinite(c.lng))return c.lat+","+c.lng;const N=((b=c.address)==null?void 0:b.trim())||"",z=/\b(via|viale|piazza|piazzale|piazzetta|corso|largo|vicolo|strada|contrada|lungomare|località|localita|borgo|parco)\b/i;return N.length>=9&&z.test(N)?[c.name,N,c.city,"Italia"].filter(Boolean).join(", "):null},wi=c=>{if(ie||he){wt("Indicazioni non disponibili finché i dettagli non sono verificati.");return}const N=Jn(c);if(!N){wt("Indirizzo non abbastanza preciso per navigare.");return}const z="https://www.google.com/maps/dir/?api=1&destination="+encodeURIComponent(N);window.open(z,"_blank","noopener,noreferrer")},In=async c=>{var N,z;if(!((N=c.address)!=null&&N.trim())){wt("Indirizzo non disponibile.");return}try{if(!((z=navigator.clipboard)!=null&&z.writeText))throw new Error("Clipboard not supported");await navigator.clipboard.writeText(c.address),wt("Indirizzo copiato.")}catch{wt("Seleziona il testo dell’indirizzo per copiarlo.")}},er=()=>{Tn("auto"),xe||H()};T.useEffect(()=>{ne==="ready"&&xe&&pt==="auto"?(Lt(""),Pt(""),Dt(!1),Kt(50),lt(1+ +(it.length>0)),k("distanza")):["denied","error","unavailable"].includes(ne)&&pt==="auto"&&Tn("none")},[ne,xe,pt]);const un=()=>{const c=jr.trim().toLocaleLowerCase("it"),N=Ut.find(z=>z.toLocaleLowerCase("it")===c);if(!N){wt("Scegli una città presente nel catalogo.");return}Fe(),Tn("manual"),Lt(N),Pt(""),Kt(100),k("data"),lt(1),Ne("esplora"),wt("Filtra per città: "+N)},Fl=()=>{Fe(),Tn("none"),Lt(""),Kt(100),lt(+(it.length>0)+ +!!Be),k("data")},Bt=s;T.useEffect(()=>se(60),[fe,ye,D,it,Be,qe,yt,m,xe,xt,D]);const kt=T.useMemo(()=>{let c=[...Bt];if(fe.trim()){const N=fe.toLowerCase();c=c.filter(z=>z.name.toLowerCase().includes(N)||z.city.toLowerCase().includes(N)||z.category.toLowerCase().includes(N)||z.tags.some(b=>b.toLowerCase().includes(N)))}if(ye==="oggi")c=c.filter(N=>N.dates.includes(ci));else if(ye==="weekend"){const N=Ml.getDay(),z=N===0?-1:6-N,b=new Date(Ml);b.setDate(b.getDate()+z);const ue=new Date(b);ue.setDate(ue.getDate()+1);const tt=an(b),ze=an(ue);c=c.filter(Xt=>Xt.dates.includes(tt)||Xt.dates.includes(ze))}else if(ye==="7giorni"){const N=new Date(Ml);N.setDate(N.getDate()+7);const z=an(N);c=c.filter(b=>b.dates.some(ue=>ue>=ci&&ue<=z))}if(D!==null&&(c=c.filter(N=>(N.dates||[]).some(z=>z>=ci&&hi(z)===D))),it.length>0&&(c=c.filter(N=>it.includes(N.category))),Be&&(c=c.filter(N=>N.region===Be)),qe&&(c=c.filter(N=>N.city===qe)),xe&&yt<100&&(c=c.filter(N=>Number.isFinite(N.distance)&&N.distance<=yt&&(xt||N.positionQuality==="precisa"))),m==="distanza"&&xe){const N=z=>z.positionQuality==="precisa"?0:z.positionQuality==="approssimata"?1:2;c.sort((z,b)=>N(z)-N(b)||(z.distance??1/0)-(b.distance??1/0))}else{const N=z=>(z.dateQuality==="confermata"?50:0)+(z.positionQuality==="precisa"?9:0)+(z.hours?5:0)+(z.category!=="Misto"?3:0);c.sort((z,b)=>{const ue=di(z.dates),tt=di(b.dates);return(ue||"9999").localeCompare(tt||"9999")||N(b)-N(z)||z.name.localeCompare(b.name,"it")})}return c},[Bt,fe,ye,D,it,Be,qe,yt,m,xe,xt]),St=T.useMemo(()=>bf(kt,{keepSingleWeeklyGroups:D!==null}),[kt,D]),Er=()=>{Xn([...it]),Zn(Be),Yt(qe),Gt(yt),P(!0)},Rl=()=>{Ln(qn),Pt(sn),Lt(Dn),Kt(xe?Mn:100);let c=0;qn.length>0&&c++,sn&&c++,Dn&&c++,xe&&Mn<100&&c++,lt(c),P(!1)},Il=()=>{Xn([]),Zn(""),Yt(""),Gt(100),Ln([]),Pt(""),Lt(""),Kt(100),lt(0),Dt(!1),P(!1)},ki=()=>{Ln([]),Pt(""),Lt(""),Kt(100),Dt(!1),lt(0),Ke(null),$(!1),Z(null),ke("")};T.useCallback((c,N,z,b)=>{const On=(N-6.5)/13*z,cn=(47.5-c)/(47.5-36.5)*b;return{x:On,y:cn}},[]);const Vt=(c,N)=>{const z=op(c.dates,c.dateQuality),b=di(c.dates),ue=Rn[c.category]||"#888",tt=w.has(c.id);return o.jsxs("div",{className:"market-card",style:{animationDelay:`${Math.min(N,12)*50}ms`,"--cat-color":ue},children:[o.jsx("button",{type:"button",className:"market-card-open","aria-label":"Apri i dettagli di "+c.name+", "+c.city,onClick:()=>qt(c)}),o.jsx("div",{style:{position:"absolute",left:0,top:0,bottom:0,width:4,background:ue,borderRadius:"4px 0 0 4px"}}),o.jsxs("div",{className:"card-top",children:[o.jsxs("div",{className:"card-badges",children:[o.jsxs("span",{className:"category-badge",style:{background:ue+"14",color:ue},children:[Fn[c.category]," ",c.category]}),z&&o.jsx("span",{className:"date-badge",style:{background:z.color},children:z.label})]}),o.jsx("button",{className:`fav-btn ${tt?"active":""}`,onClick:ze=>zr(c.id,ze),"aria-label":tt?"Rimuovi dai preferiti":"Aggiungi ai preferiti",children:o.jsx(je,{name:tt?"heartFilled":"heart",size:20})})]}),o.jsx("div",{className:"card-name",children:c.name}),o.jsxs("div",{className:"card-info",children:[o.jsxs("span",{className:"card-info-item",children:[o.jsx(je,{name:"calendar",size:14,color:"#6C6255"}),Na(b)]}),o.jsxs("span",{className:"card-info-item",children:[o.jsx(je,{name:"clock",size:14,color:"#6C6255"}),c.hours||"Orari da verificare"]}),o.jsxs("span",{className:"card-info-item",children:[o.jsx(je,{name:"mapPin",size:14,color:"#6C6255"}),c.city]}),xe&&o.jsx("span",{className:"card-info-item card-distance",children:c.positionQuality==="precisa"&&Number.isFinite(c.distance)?"a "+Math.round(c.distance)+" km":c.positionQuality==="approssimata"&&Number.isFinite(c.distance)?"circa "+Math.round(c.distance)+" km (stimati)":"Posizione da verificare"})]})]},c.id)},Si=()=>o.jsx(T.Suspense,{fallback:o.jsx("div",{role:"status",style:{margin:"22px 18px 110px",padding:22,background:"var(--white)",borderRadius:12,color:"var(--ink-lighter)"},children:"Caricamento mappa interattiva…"}),children:o.jsx(ep,{markets:kt,userLat:ee,userLng:ve,onSelect:qt})}),ji=()=>{var tt;if(!q)return null;const c=q,N=Rn[c.category]||"#888",z=w.has(c.id),b=c.dates.filter(ze=>ze>=ci).sort(),ue=!ie&&!he&&!!Jn(c);return o.jsxs("div",{className:"detail-page",children:[o.jsxs("div",{className:"detail-hero",style:{background:`linear-gradient(135deg, ${N}08 0%, ${N}14 100%)`},children:[o.jsx("div",{style:{position:"absolute",top:-40,right:-40,width:180,height:180,borderRadius:"50%",background:N,opacity:.04}}),o.jsx("button",{className:"detail-back",onClick:yi,children:o.jsx(je,{name:"chevronLeft",size:20})}),o.jsxs("div",{className:"detail-actions-top",children:[o.jsx("button",{className:"detail-icon-btn",onClick:()=>xi(c),"aria-label":"Condividi questo mercato",children:o.jsx(je,{name:"share",size:18})}),o.jsx("button",{className:`detail-icon-btn ${z?"fav-active":""}`,onClick:()=>zr(c.id),children:o.jsx(je,{name:z?"heartFilled":"heart",size:18})})]}),o.jsxs("span",{className:"detail-category-tag",style:{background:N+"18",color:N},children:[Fn[c.category]," ",c.category]}),o.jsx("div",{className:"detail-name",children:c.name}),ie&&o.jsx("div",{style:{fontSize:12,marginTop:8},children:"Caricamento dettagli completi…"}),he&&o.jsxs("div",{role:"alert",style:{fontSize:12,marginTop:8},children:[he,". Sono visibili i dati sintetici."]}),o.jsxs("div",{className:"detail-city",children:[o.jsx(je,{name:"mapPin",size:14,color:N,strokeWidth:2})," ",c.city,", ",c.region]})]}),o.jsxs("div",{className:"detail-body",children:[o.jsxs("div",{className:"detail-section",style:{animationDelay:"0.05s"},children:[o.jsxs("div",{className:"detail-section-title",children:[o.jsx(je,{name:"calendar",size:18,color:N})," Prossime date"]}),o.jsxs("div",{className:"detail-dates-chips",children:[b.length===0&&o.jsx("span",{className:"date-chip",children:"Date da verificare"}),b.map(ze=>{const Xt=ze===ci,On=new Date(ze+"T00:00:00").getDay(),cn=On===0||On===6;return o.jsx("span",{className:`date-chip ${Xt?"today":cn?"weekend":""}`,children:Na(ze)},ze)})]}),c.recurrence&&o.jsx("div",{className:"detail-recurrence",children:c.recurrence}),Ea(c.dates,c.dateQuality)&&o.jsx("div",{style:{fontSize:12,color:"#6C6255",marginTop:8},children:Ea(c.dates,c.dateQuality)})]}),o.jsxs("div",{className:"detail-section",style:{animationDelay:"0.1s"},children:[o.jsxs("div",{className:"detail-section-title",children:[o.jsx(je,{name:"clock",size:18,color:N})," Orari"]}),o.jsx("div",{className:"detail-hours",children:c.hours||"Orari non disponibili"})]}),o.jsxs("div",{className:"detail-section",style:{animationDelay:"0.15s"},children:[o.jsxs("div",{className:"detail-section-title",children:[o.jsx(je,{name:"mapPin",size:18,color:N})," Indirizzo"]}),o.jsx("div",{className:"detail-address",children:c.address||"Indirizzo non verificato"}),c.locationReviewRequired&&o.jsxs("p",{role:"note",style:{color:"#857660",fontSize:12,lineHeight:1.5,margin:"9px 0"},children:[kf," Le indicazioni stradali per questa scheda sono disabilitate."]}),c.positionQuality!=="precisa"&&o.jsx("div",{style:{fontSize:12,color:"#6C6255",marginTop:6},children:"Posizione indicativa o da verificare"}),!ue&&!ie&&o.jsx("div",{role:"note",style:{fontSize:12,color:"#6C6255",margin:"10px 0"},children:"Indicazioni non disponibili: manca una sede riconciliata e verificabile."}),o.jsxs("div",{className:"detail-address-actions",children:[o.jsxs("button",{className:"btn-primary",onClick:()=>wi(c),disabled:!ue,title:ue?"Apri indicazioni stradali":"Dettagli o sede non sufficienti per navigare",children:[o.jsx(je,{name:"navigation",size:16,color:"white"})," Indicazioni"]}),o.jsxs("button",{className:"btn-secondary",onClick:()=>In(c),disabled:!((tt=c.address)!=null&&tt.trim()),children:[o.jsx(je,{name:"copy",size:16})," Copia"]})]})]}),c.description&&o.jsxs("div",{className:"detail-section",style:{animationDelay:"0.2s"},children:[o.jsxs("div",{className:"detail-section-title",children:[o.jsx(je,{name:"info",size:18,color:N})," Descrizione"]}),o.jsx("div",{className:"detail-description",children:c.description})]}),c.tags&&c.tags.length>0&&o.jsxs("div",{className:"detail-section",style:{animationDelay:"0.25s"},children:[o.jsx("div",{className:"detail-section-title",children:"Tag"}),o.jsx("div",{className:"detail-tags",children:c.tags.map(ze=>o.jsx("span",{className:"detail-tag",children:ze},ze))})]}),o.jsx("div",{className:"detail-section",style:{animationDelay:"0.3s"},children:o.jsxs("div",{className:"detail-provenance",children:[o.jsxs("div",{style:{flex:1},children:[o.jsx("div",{style:{fontSize:13,marginBottom:2},children:c.lastVerified?"Verificato il "+c.lastVerified:"Non verificato di recente"}),o.jsxs("div",{style:{fontSize:12,opacity:.7},children:["Fonte: ",c.source||"non disponibile",c.sourceUpdated?c.sourceUpdateScope==="dataset"?" · dataset aggiornato il "+c.sourceUpdated+" (non verifica del singolo mercato)":" · dati del "+c.sourceUpdated:""]}),c.sourceUrl&&o.jsx("a",{href:c.sourceUrl,target:"_blank",rel:"noopener noreferrer",style:{display:"inline-block",fontSize:12,marginTop:5},children:"Controlla la fonte originale"}),(c.sourceEvidence||[]).filter(ze=>ze.url!==c.sourceUrl).slice(0,3).map((ze,Xt)=>o.jsxs("div",{style:{fontSize:12,marginTop:5,lineHeight:1.4},children:["Fonte aggiuntiva:"," ",o.jsx("a",{href:ze.url,target:"_blank",rel:"noopener noreferrer",children:ze.nome})]},ze.url+Xt))]}),o.jsxs("div",{style:{textAlign:"right"},children:[o.jsx("div",{style:{fontSize:11,marginBottom:4},children:"Completezza dati"}),o.jsx("div",{className:"confidence-bar",children:o.jsx("div",{className:"confidence-fill",style:{width:`${c.dataCompleteness}%`,background:c.dataCompleteness>80?"#446E47":c.dataCompleteness>55?"#805B08":"#B94439"}})}),o.jsx("div",{style:{fontSize:10,maxWidth:135,marginTop:5},children:"Campi compilati, non verifica delle informazioni"})]})]})}),o.jsx("div",{style:{height:40}})]})]})},Ol=()=>o.jsxs(o.Fragment,{children:[o.jsx("div",{className:"filter-overlay",onClick:()=>P(!1)}),o.jsxs("div",{className:"filter-panel",children:[o.jsxs("div",{className:"filter-header",children:[o.jsx("span",{className:"filter-title",children:"Filtri"}),o.jsx("button",{className:"filter-close",onClick:()=>P(!1),children:o.jsx(je,{name:"x",size:18})})]}),o.jsxs("div",{className:"filter-body",children:[o.jsxs("div",{className:"filter-section",children:[o.jsx("div",{className:"filter-section-label",children:"Categoria"}),o.jsx("div",{className:"filter-categories",children:Nr.map(c=>{const N=qn.includes(c),z=Rn[c];return o.jsxs("button",{className:`filter-cat-chip ${N?"active":""}`,style:N?{borderColor:z,color:z,background:z+"10"}:{},onClick:()=>{Xn(b=>b.includes(c)?b.filter(ue=>ue!==c):[...b,c])},children:[Fn[c]," ",c]},c)})})]}),o.jsxs("div",{className:"filter-section",children:[o.jsx("div",{className:"filter-section-label",children:"Regione"}),o.jsxs("select",{className:"filter-select",value:sn,onChange:c=>{Zn(c.target.value),Yt("")},children:[o.jsx("option",{value:"",children:"Tutte le regioni"}),Cr.map(c=>o.jsx("option",{value:c,children:c},c))]})]}),o.jsxs("div",{className:"filter-section",children:[o.jsx("div",{className:"filter-section-label",children:"Città"}),o.jsxs("select",{className:"filter-select",value:Dn,onChange:c=>Yt(c.target.value),children:[o.jsx("option",{value:"",children:"Tutte le città"}),Ut.filter(c=>{var N;return!sn||((N=s.find(z=>z.city===c))==null?void 0:N.region)===sn}).map(c=>o.jsx("option",{value:c,children:c},c))]})]}),o.jsxs("div",{className:"filter-section",children:[o.jsx("div",{className:"filter-section-label",children:"Distanza massima"}),o.jsxs("div",{className:"range-container",children:[o.jsxs("div",{className:"range-label",children:[o.jsx("span",{children:"0 km"}),o.jsxs("span",{className:"range-value",children:[Mn," km"]})]}),o.jsx("input",{type:"range",className:"range-input",min:5,max:100,step:5,value:Mn,disabled:!xe,onChange:c=>Gt(Number(c.target.value))}),!xe&&o.jsx("div",{className:"setting-sublabel",children:"Per usare il raggio, attiva la posizione in Impostazioni."})]})]})]}),o.jsxs("div",{className:"filter-footer",children:[o.jsx("button",{className:"filter-reset",onClick:Il,children:"Reimposta filtri"}),o.jsx("button",{className:"filter-apply",onClick:Rl,children:"Applica filtri"})]})]})]}),_r=()=>o.jsxs(o.Fragment,{children:[o.jsxs("div",{className:"header",children:[o.jsxs("div",{className:"header-title",children:[o.jsx("span",{className:"accent",children:"Mercati"})," d'Italia"]}),o.jsxs("div",{className:"search-container",children:[o.jsx("span",{className:"search-icon",children:o.jsx(je,{name:"search",size:18})}),o.jsx("input",{className:"search-input",placeholder:"Cerca città, mercato o parola chiave",value:fe,onChange:c=>ke(c.target.value)})]}),o.jsx("div",{className:"chips-row",children:[{key:"oggi",label:"Oggi"},{key:"weekend",label:"Questo weekend"},{key:"7giorni",label:"Prossimi 7 giorni"}].map(({key:c,label:N})=>o.jsx("button",{className:`chip ${ye===c?"active":""}`,onClick:()=>{Ke(ye===c?null:c),$(!0)},children:N},c))}),de==="lista"&&o.jsxs("div",{className:"chips-row","aria-label":"Filtra per giorno della settimana",style:{gap:5,marginTop:3,paddingBottom:5,flexWrap:"nowrap",overflowX:"auto",scrollbarWidth:"thin"},children:[gc.map((c,N)=>o.jsx("button",{type:"button","aria-pressed":D===N,"aria-label":"Mostra mercati del "+["lunedì","martedì","mercoledì","giovedì","venerdì","sabato","domenica"][N],className:`chip ${D===N?"active":""}`,style:{flexShrink:0,minWidth:39,padding:"7px 10px",fontSize:12},onClick:()=>{Z(z=>z===N?null:N),D!==N&&Ke("7giorni")},children:c},c)),D!==null&&o.jsx("button",{type:"button",className:"chip",style:{flexShrink:0,padding:"7px 9px"},onClick:()=>Z(null),"aria-label":"Togli filtro giorno",children:"×"})]}),de==="lista"&&!xe&&!qe&&!Be&&!fe.trim()&&o.jsxs("div",{role:"note",style:{background:"#F0EEE8",borderRadius:12,padding:"12px 14px",margin:"6px 0 12px",fontSize:12,lineHeight:1.5,color:"var(--ink-light)"},children:[o.jsx("strong",{style:{display:"block",marginBottom:3,fontSize:13,color:"var(--ink)"},children:"Stai esplorando tutta Italia"}),"Cerca la tua città nella barra sopra, oppure usa la posizione per trovare mercati nella tua zona. Le date automatiche non sono conferme degli organizzatori.",o.jsx("div",{style:{display:"flex",gap:6,marginTop:9,flexWrap:"wrap"},children:["Firenze","Roma","Milano"].map(c=>o.jsx("button",{type:"button",className:"chip",onClick:()=>{Pt(""),Lt(c),lt(1),Me("lista")},children:c},c))})]}),(qe||Be||it.length>0)&&o.jsxs("div",{className:"chips-row",style:{gap:8,alignItems:"center",margin:"2px 0 8px"},children:[qe&&o.jsxs("button",{className:"chip active",onClick:()=>{Lt(""),lt(Math.max(0,ft-1))},"aria-label":"Rimuovi filtro città "+qe,children:["Città: ",qe," ×"]}),Be&&o.jsxs("button",{className:"chip active",onClick:()=>{Pt(""),lt(Math.max(0,ft-1))},"aria-label":"Rimuovi filtro regione "+Be,children:["Regione: ",Be," ×"]}),it.length>0&&o.jsx("button",{className:"chip active",onClick:()=>{Ln([]),lt(Math.max(0,ft-1))},children:"Categorie ×"}),o.jsx("button",{className:"chip",onClick:ki,children:"Azzera filtri"})]}),o.jsxs("div",{className:"chips-row",style:{marginTop:8,alignItems:"center"},children:[o.jsxs("button",{className:`chip ${xe?"active":""}`,onClick:er,disabled:ne==="requesting",children:[o.jsx(je,{name:"mapPin",size:13}),ne==="ready"?xt?"Vicino a me · posizioni indicative":"Vicino a me · 50 km, posizioni precise":ne==="requesting"?"Cerco la posizione…":"Mercati vicino a me"]}),te&&o.jsx("span",{role:"alert",style:{fontSize:12,color:"#A5443D"},children:te})]}),xe&&yt<100&&o.jsxs("div",{role:"note",style:{fontSize:12,lineHeight:1.5,color:"#7D7267",margin:"4px 20px 10px"},children:[xt?"Mostriamo anche mercati con coordinate non verificate. Alcuni possono non essere davvero vicini.":"Nel raggio mostriamo solo mercati con posizione precisa. Altri mercati possono mancare.",o.jsx("button",{className:"chip",style:{display:"block",marginTop:8},onClick:()=>Dt(c=>!c),children:xt?"Escludi posizioni indicative":"Mostra anche posizioni indicative"})]}),o.jsxs("div",{className:"controls-row",children:[o.jsxs("div",{className:"view-toggle",children:[o.jsxs("button",{className:de==="lista"?"active":"",onClick:()=>Me("lista"),children:[o.jsx(je,{name:"list",size:14})," Lista"]}),o.jsxs("button",{className:de==="mappa"?"active":"",onClick:()=>Me("mappa"),children:[o.jsx(je,{name:"map",size:14})," Mappa"]})]}),o.jsxs("div",{style:{position:"relative"},children:[o.jsxs("button",{className:"sort-btn",onClick:()=>F(!B),children:[o.jsx(je,{name:"sort",size:14})," Ordina"]}),B&&o.jsx("div",{className:"sort-dropdown",children:[{key:"data",label:"Data",icon:"calendar"},{key:"distanza",label:"Distanza",icon:"mapPin"}].map(({key:c,label:N,icon:z})=>o.jsxs("button",{className:`sort-option ${m===c?"active":""}`,disabled:c==="distanza"&&!xe,title:c==="distanza"&&!xe?"Attiva la posizione per ordinare per distanza":"",onClick:()=>{k(c),F(!1)},children:[o.jsx(je,{name:z,size:16})," ",N,m===c&&o.jsx(je,{name:"check",size:16,color:"#B94439"})]},c))})]}),o.jsxs("button",{className:`filter-btn ${ft>0?"has-filters":""}`,onClick:Er,children:[o.jsx(je,{name:"filter",size:14})," Filtri",ft>0&&o.jsx("span",{className:"filter-count",children:ft})]})]})]}),o.jsxs("div",{className:"results-count",style:{display:"flex",alignItems:"center",justifyContent:"space-between"},children:[o.jsxs("span",{children:[h?"Caricamento mercati statici...":`${kt.length.toLocaleString("it-IT")} ${ye?"appuntament"+(kt.length===1?"o":"i")+" "+(ye==="oggi"?"previsti oggi":ye==="weekend"?"previsti nel weekend":"previsti nei prossimi 7 giorni"):"sched"+(kt.length===1?"a":"e")+" nel catalogo"}${qe?" · "+qe:Be?" · "+Be:xe?"":" · Italia"}`,de==="lista"&&St.length<kt.length&&!h&&` · ${St.length.toLocaleString("it-IT")} schede`]}),K==="demo"&&o.jsx("span",{style:{fontSize:10,fontWeight:700,letterSpacing:"0.05em",padding:"2px 8px",borderRadius:100,background:"var(--sand)",color:"var(--ink-lighter)"},children:"DEMO"})]}),f&&!h&&o.jsxs("div",{role:"alert",className:"empty-state",children:[o.jsx("div",{className:"empty-title",children:"Catalogo temporaneamente non disponibile"}),o.jsx("div",{className:"empty-text",children:f})]}),h?o.jsx("div",{className:"markets-list",children:[1,2,3].map(c=>o.jsx("div",{className:"market-card",style:{height:120,animation:"none",background:"linear-gradient(90deg, var(--white) 25%, var(--beige) 50%, var(--white) 75%)",backgroundSize:"200% 100%",animationName:"shimmer",animationDuration:"1.5s",animationIterationCount:"infinite",animationTimingFunction:"linear"}},c))}):de==="lista"?o.jsx("div",{className:"markets-list",children:St.length>0?o.jsxs(o.Fragment,{children:[St.slice(0,ae).map((c,N)=>c.kind==="group"?o.jsx(Zf,{group:c,loadMarket:E,onOpenMarket:qt,selectedWeekday:D,autoExpand:Wf(c,D,qe,fe)},c.key):Vt(c.market,N)),ae<St.length&&o.jsxs("button",{className:"btn-secondary",onClick:()=>se(c=>c+60),style:{margin:"18px auto 30px",padding:"12px 24px",display:"block"},children:["Mostra altre schede (",Math.min(ae,St.length)," di ",St.length,")"]})]}):o.jsxs("div",{className:"empty-state",children:[o.jsx("div",{className:"empty-icon",children:"🔍"}),o.jsx("div",{className:"empty-title",children:"Nessun mercato trovato"}),o.jsx("div",{className:"empty-text",children:xe&&yt<100&&!xt?"Nessun mercato con posizione precisa in questo raggio e periodo. Puoi includere quelli con posizione indicativa.":"Prova a cambiare data, distanza, città o categoria."}),xe&&yt<100&&!xt&&o.jsx("button",{className:"btn-secondary",style:{padding:"10px 18px",marginTop:12},onClick:()=>Dt(!0),children:"Mostra posizioni indicative"}),o.jsx("button",{style:{marginTop:16,padding:"10px 24px",background:"var(--terracotta)",color:"white",border:"none",borderRadius:100,fontFamily:"var(--font-body)",fontSize:14,fontWeight:600,cursor:"pointer"},onClick:ki,children:"Reimposta"})]})}):Si()]}),Ni=()=>{const c=Bt.filter(N=>w.has(N.id));return o.jsxs(o.Fragment,{children:[o.jsx("div",{className:"header",children:o.jsx("div",{className:"header-title",children:"Preferiti"})}),o.jsx("div",{className:"page-content",children:c.length>0?o.jsx("div",{className:"markets-list",style:{padding:0},children:c.map((N,z)=>Vt(N,z))}):o.jsxs("div",{className:"empty-state",children:[o.jsx("div",{className:"empty-icon",children:"❤️"}),o.jsx("div",{className:"empty-title",children:"Nessun preferito"}),o.jsx("div",{className:"empty-text",children:"Salva i mercati che ti interessano per ritrovarli qui."})]})})]})},Ci=()=>{const c=Bt.filter(b=>w.has(b.id)),N=c.map(b=>({market:b,next:di(b.dates)})).filter(b=>b.next).sort((b,ue)=>b.next.localeCompare(ue.next)).slice(0,30),z=c.filter(b=>!di(b.dates));return o.jsxs(o.Fragment,{children:[o.jsx("div",{className:"header",children:o.jsx("div",{className:"header-title",children:"Agenda preferiti"})}),o.jsxs("div",{className:"page-content",children:[o.jsxs("div",{className:"setting-card",children:[o.jsx("div",{className:"setting-label",children:"I prossimi mercati che hai salvato"}),o.jsx("div",{className:"setting-sublabel",children:"Qui trovi le date disponibili. Le notifiche push automatiche non sono ancora attive. Controlla sempre se la data è confermata prima di partire."})]}),c.length===0?o.jsxs("div",{className:"empty-state",children:[o.jsx("div",{className:"empty-icon",children:"♡"}),o.jsx("div",{className:"empty-title",children:"Nessun mercato salvato"}),o.jsx("div",{className:"empty-text",children:"Salva un mercato dalla ricerca per vederlo qui."}),o.jsx("button",{className:"btn-primary",style:{padding:"10px 20px",marginTop:12},onClick:()=>Ne("esplora"),children:"Cerca mercati"})]}):o.jsxs(o.Fragment,{children:[N.length>0?o.jsx("div",{className:"markets-list",style:{padding:0},children:N.map(({market:b,next:ue},tt)=>o.jsxs("button",{className:"setting-card",style:{display:"flex",width:"100%",textAlign:"left",gap:12,alignItems:"center",cursor:"pointer",border:"none"},onClick:()=>qt(b),children:[o.jsx("span",{style:{minWidth:85,fontWeight:700},children:Na(ue)}),o.jsxs("span",{style:{flex:1},children:[o.jsx("strong",{children:b.name}),o.jsxs("span",{style:{display:"block",fontSize:12,opacity:.75},children:[b.city," · ",b.dateQuality==="confermata"?"Confermata":"Prevista, da verificare"]})]})]},b.id))}):o.jsx("div",{className:"setting-card",children:"Nessuna data futura disponibile per i tuoi preferiti."}),z.length>0&&o.jsxs("div",{className:"setting-card",style:{marginTop:12},children:[o.jsxs("div",{className:"setting-label",children:[z.length," preferiti senza prossima data"]}),o.jsx("div",{className:"setting-sublabel",children:"Li trovi nella sezione Preferiti. Verifica la fonte ufficiale."})]})]})]})]})},zi=()=>o.jsxs(o.Fragment,{children:[o.jsx("div",{className:"header",children:o.jsx("div",{className:"header-title",children:"Impostazioni"})}),o.jsxs("div",{className:"page-content",children:[o.jsxs("div",{className:"setting-card",children:[o.jsx("div",{className:"setting-label",style:{marginBottom:4},children:"Posizione"}),o.jsx("div",{className:"setting-sublabel",children:"Scegli come trovare i mercati vicino a te"}),o.jsxs("div",{className:"location-options",children:[o.jsxs("button",{className:`location-option ${pt==="auto"?"active":""}`,onClick:er,children:[o.jsx("div",{className:"icon-circle",children:o.jsx(je,{name:"compass",size:18})}),o.jsxs("div",{children:[o.jsx("div",{style:{fontWeight:600},children:"Usa la mia posizione"}),o.jsx("div",{style:{fontSize:12,color:"#6C6255",marginTop:1},children:ne==="ready"?"Posizione attiva":ne==="requesting"?"Richiesta in corso…":"Richiede il tuo consenso"})]})]}),o.jsxs("button",{className:`location-option ${pt==="manual"?"active":""}`,onClick:()=>Tn("manual"),children:[o.jsx("div",{className:"icon-circle",children:o.jsx(je,{name:"mapPin",size:18})}),o.jsxs("div",{children:[o.jsx("div",{style:{fontWeight:600},children:"Scegli una città"}),o.jsx("div",{style:{fontSize:12,color:"#6C6255",marginTop:1},children:"Inserisci manualmente"})]})]}),o.jsxs("button",{className:`location-option ${pt==="none"?"active":""}`,onClick:Fl,children:[o.jsx("div",{className:"icon-circle",children:o.jsx(je,{name:"x",size:18})}),o.jsxs("div",{children:[o.jsx("div",{style:{fontWeight:600},children:"Non ora"}),o.jsx("div",{style:{fontSize:12,color:"#6C6255",marginTop:1},children:"Naviga senza posizione"})]})]})]}),te&&o.jsx("div",{role:"alert",className:"setting-sublabel",style:{marginTop:12},children:te}),xe&&o.jsx("div",{className:"setting-sublabel",style:{marginTop:10},children:"Distanze calcolate rispetto alla tua posizione. Alcuni mercati hanno solo coordinate indicative."}),pt==="manual"&&o.jsxs(o.Fragment,{children:[o.jsxs("div",{className:"manual-city-input",children:[o.jsx("input",{list:"available-market-cities",placeholder:"Es. Firenze",value:jr,onChange:c=>gi(c.target.value),onKeyDown:c=>{c.key==="Enter"&&un()}}),o.jsx("datalist",{id:"available-market-cities",children:Ut.map(c=>o.jsx("option",{value:c},c))}),o.jsx("button",{onClick:un,children:"Filtra città"})]}),o.jsx("div",{className:"setting-sublabel",children:"La città selezionata filtra i risultati. Non equivale alla posizione GPS."})]})]}),o.jsxs("div",{className:"app-version",children:[o.jsxs("div",{style:{fontFamily:"var(--font-display)",fontSize:16,marginBottom:4},children:[o.jsx("span",{style:{color:"var(--terracotta)"},children:"Mercati"})," d'Italia"]}),"Versione 1.1 · Catalogo statico (lettura gratuita)"]})]})]});return o.jsxs(o.Fragment,{children:[o.jsx("style",{children:ap}),o.jsxs("div",{className:"app-container",onClick:()=>B&&F(!1),children:[we==="esplora"&&_r(),we==="mappa"&&_r(),we==="preferiti"&&Ni(),we==="notifiche"&&Ci(),we==="impostazioni"&&zi(),G&&Ol(),q&&ji(),Se&&o.jsx("div",{className:"toast",children:Se}),o.jsx("nav",{className:"bottom-tabs",children:[{id:"esplora",label:"Esplora",icon:"compass"},{id:"preferiti",label:"Preferiti",icon:"heart"},{id:"notifiche",label:"Agenda",icon:"calendar"},{id:"impostazioni",label:"Impostazioni",icon:"settings"}].map(c=>o.jsxs("button",{className:`tab-btn ${we===c.id?"active":""}`,onClick:()=>{Ne(c.id),c.id==="esplora"&&Me("lista")},children:[o.jsx(je,{name:c.icon,size:22,strokeWidth:we===c.id?2:1.6}),c.label]},c.id))})]})]})}mf.createRoot(document.getElementById("root")).render(o.jsx(af.StrictMode,{children:o.jsx(sp,{})}));export{o as j,T as r};
