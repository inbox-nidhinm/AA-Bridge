"""The original rounds many inside joints (K's crotch, the joints of M, V, W, X, Y...) with a
fillet: a separate piece laid into the corner, a curve tangent to both edges. Narrowing a
letter moves it towards a heavier drawing (for the Bold, past the original's Bold), and
there a fillet's straight-line move no longer follows its corner, which moves along the
crossing of two edges. So after narrowing, each fillet is laid into its corner again, as
the original lays it: the same legs along each edge and the same handle tension, on the
narrowed outline. Serif brackets (between an upright and a flat edge) move with their
corner and are left as they are."""
import math
import pathops

MATCH = 40      # units: how far a narrowed corner may sit from where its fillet points


def _unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n else (0.0, 0.0)


def _meet(p, d, q, e):
    """Where the lines p + s*d and q + t*e cross: (point, s, t), or None if parallel."""
    det = d[0] * e[1] - d[1] * e[0]
    if abs(det) < 1e-9: return None
    s = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / det
    t = ((q[0] - p[0]) * d[1] - (q[1] - p[1]) * d[0]) / det
    return (p[0] + d[0] * s, p[1] + d[1] * s), s, t


def pieces(contours):
    """(contour index, S, H1, H2, E, back nodes) node indices of every fillet-shaped piece:
    seven nodes, an arc from S to E, and three nodes tucked inside the letter."""
    out = []
    for ci, c in enumerate(contours):
        if len(c) != 7 or [n[2] for n in c].count('offcurve') != 2: continue
        h1 = next(i for i, n in enumerate(c) if n[2] == 'offcurve' and c[(i + 1) % 7][2] == 'offcurve')
        s, h2, e = (h1 - 1) % 7, (h1 + 1) % 7, (h1 + 2) % 7
        if c[e][2] != 'curve': continue
        out.append((ci, s, h1, h2, e, [(e + k) % 7 for k in (1, 2, 3)]))
    return out


def _corner(c, s, h1, h2, e):
    """Where the fillet's two edges meet: its tangent lines at S and E crossed."""
    S, E = c[s], c[e]
    m = _meet(S, _unit((c[h1][0] - S[0], c[h1][1] - S[1])), E, _unit((c[h2][0] - E[0], c[h2][1] - E[1])))
    return m and m[0]


def _bracket(c, s, h1, h2, e):
    d1 = _unit((c[h1][0] - c[s][0], c[h1][1] - c[s][1]))
    d2 = _unit((c[h2][0] - c[e][0], c[h2][1] - c[e][1]))
    axis = lambda d: min(abs(d[0]), abs(d[1])) < 0.02
    return axis(d1) and axis(d2)


# --- the letter's merged outline, as segments ('L' or 'C', p0, a, b, p1)
def _path(contours):
    p = pathops.Path()
    pen = p.getPen()
    for c in contours:
        start = max(i for i, n in enumerate(c) if n[2] != 'offcurve')
        seq = c[start + 1:] + c[:start + 1]
        pen.moveTo(tuple(c[start][:2]))
        off = []
        for n in seq:
            if n[2] == 'offcurve': off.append(tuple(n[:2]))
            elif n[2] == 'curve': pen.curveTo(*off, tuple(n[:2])); off = []
            else: pen.lineTo(tuple(n[:2])); off = []
        pen.closePath()
    p.simplify(fix_winding=True)
    return p


def _segments(p):
    out, cur, start, last = [], [], None, None
    for verb, pts in p.segments:
        if verb == 'moveTo':
            start = last = pts[0]; cur = []
        elif verb == 'lineTo':
            cur.append(('L', last, last, pts[0], pts[0])); last = pts[0]
        elif verb == 'curveTo':
            cur.append(('C', last, pts[0], pts[1], pts[2])); last = pts[2]
        elif verb == 'qCurveTo':
            q, e = pts[0], pts[-1]
            cur.append(('C', last, (last[0] + 2 / 3 * (q[0] - last[0]), last[1] + 2 / 3 * (q[1] - last[1])),
                        (e[0] + 2 / 3 * (q[0] - e[0]), e[1] + 2 / 3 * (q[1] - e[1])), e)); last = e
        elif verb in ('closePath', 'endPath'):
            if cur and math.dist(last, start) > 1e-6: cur.append(('L', last, last, start, start))
            if cur: out.append(cur)
            cur = []
    return out


def _bez(seg, t):
    _, p0, a, b, p1 = seg
    m = 1 - t
    return (m ** 3 * p0[0] + 3 * m * m * t * a[0] + 3 * m * t * t * b[0] + t ** 3 * p1[0],
            m ** 3 * p0[1] + 3 * m * m * t * a[1] + 3 * m * t * t * b[1] + t ** 3 * p1[1])


def _walk(seg, from_end, dist):
    """The point at arc length dist from one end of a segment, and the direction there
    pointing back towards that end."""
    pts = [_bez(seg, i / 64) for i in range(65)]
    if from_end: pts = pts[::-1]
    acc = 0.0
    for q0, q1 in zip(pts, pts[1:]):
        step = math.dist(q0, q1)
        if acc + step >= dist and step:
            t = (dist - acc) / step
            return (q0[0] + (q1[0] - q0[0]) * t, q0[1] + (q1[1] - q0[1]) * t), _unit((q0[0] - q1[0], q0[1] - q1[1]))
        acc += step
    return pts[-1], _unit((pts[-2][0] - pts[-1][0], pts[-2][1] - pts[-1][1]))


def _inside_corners(segs):
    """(corner, incoming segment, outgoing segment) for every sharp inside corner."""
    found = []
    for c in segs:
        pts = [s[1] for s in c]
        area = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1]))
        for i in range(len(c)):
            sin, sout = c[i - 1], c[i]
            p = sin[4]
            din = _unit((p[0] - sin[3][0], p[1] - sin[3][1])) if sin[0] == 'C' else _unit((p[0] - sin[1][0], p[1] - sin[1][1]))
            dout = _unit((sout[2][0] - p[0], sout[2][1] - p[1])) if sout[0] == 'C' else _unit((sout[4][0] - p[0], sout[4][1] - p[1]))
            cross = din[0] * dout[1] - din[1] * dout[0]
            turn = math.degrees(math.atan2(cross, din[0] * dout[0] + din[1] * dout[1]))
            if abs(turn) >= 10 and turn * area < 0:
                found.append((p, sin, sout))
    return found


def refit(contours, drawing, real):
    """Lay every fillet of a narrowed letter (contours) back into its corner, measured
    from the same letter as drawn (drawing). Only the first `real` contours are outline."""
    todo = [f for f in pieces(drawing[:real]) if not _bracket(drawing[f[0]], *f[1:5])]
    if not todo: return 0
    skip = {f[0] for f in todo}
    corners = _inside_corners(_segments(_path([c for i, c in enumerate(contours[:real]) if i not in skip])))
    done = 0
    for ci, s, h1, h2, e, back in todo:
        d, c = drawing[ci], contours[ci]
        P0, Pc = _corner(d, s, h1, h2, e), _corner(c, s, h1, h2, e)
        if P0 is None or Pc is None: continue
        near = [k for k in corners if math.dist(k[0], Pc) < MATCH]
        if not near: continue
        P, sin, sout = min(near, key=lambda k: math.dist(k[0], Pc))
        # which edge S lies on: the one leaving the corner closest to S's direction
        toS = _unit((c[s][0] - Pc[0], c[s][1] - Pc[1]))
        back_in = _unit((sin[1][0] - P[0], sin[1][1] - P[1]) if sin[0] == 'L' else (sin[3][0] - P[0], sin[3][1] - P[1]))
        out = _unit((sout[4][0] - P[0], sout[4][1] - P[1]) if sout[0] == 'L' else (sout[2][0] - P[0], sout[2][1] - P[1]))
        s_on_in = toS[0] * back_in[0] + toS[1] * back_in[1] >= toS[0] * out[0] + toS[1] * out[1]
        # the original's legs and handle tension at this weight
        rS, rE = math.dist(d[s][:2], P0), math.dist(d[e][:2], P0)
        kS = math.dist(d[h1][:2], d[s][:2]) / max(rS, 1e-6)
        kE = math.dist(d[h2][:2], d[e][:2]) / max(rE, 1e-6)
        S, tS = _walk(sin, True, rS) if s_on_in else _walk(sout, False, rS)
        E, tE = _walk(sout, False, rE) if s_on_in else _walk(sin, True, rE)
        # (_walk starts at the corner, so tS and tE point from S and E towards it)
        m = _meet(S, tS, E, tE)
        dS, dE = (m[1], m[2]) if m and m[1] > 0 and m[2] > 0 else (rS, rE)
        H1 = (S[0] + tS[0] * kS * dS, S[1] + tS[1] * kS * dS)
        H2 = (E[0] + tE[0] * kE * dE, E[1] + tE[1] * kE * dE)
        # the nodes inside the letter keep their place against the corner and its two edges
        uS0, uE0 = _unit((d[s][0] - P0[0], d[s][1] - P0[1])), _unit((d[e][0] - P0[0], d[e][1] - P0[1]))
        uS, uE = _unit((S[0] - P[0], S[1] - P[1])), _unit((E[0] - P[0], E[1] - P[1]))
        det = uS0[0] * uE0[1] - uS0[1] * uE0[0]
        if abs(det) < 1e-6: continue
        for k in back:
            vx, vy = d[k][0] - P0[0], d[k][1] - P0[1]
            a = (vx * uE0[1] - vy * uE0[0]) / det
            b = (uS0[0] * vy - uS0[1] * vx) / det
            c[k][:2] = [P[0] + a * uS[0] + b * uE[0], P[1] + a * uS[1] + b * uE[1]]
        c[s][:2], c[h1][:2], c[h2][:2], c[e][:2] = list(S), list(H1), list(H2), list(E)
        done += 1
    return done
