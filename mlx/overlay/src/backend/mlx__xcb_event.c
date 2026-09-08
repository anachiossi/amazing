

#include	<xcb/xcb.h>
#include	<xcb/xcb_keysyms.h>

#include	"mlx__xcb_internal.h"


/* works for key press & key release, xcb struct is identical */
void mlx__xcb_event_key(mlx__xcb_t *mlx_xcb, mlx__xcb_win_t *win,
			xcb_key_press_event_t *ev)
{
  xcb_keysym_t ks;
  int	(*f)(unsigned int, void *);
  uint8_t type;

  type = ev->response_type & ~0x80;
  ks = xcb_key_press_lookup_keysym(mlx_xcb->keysymbols, ev, 0);
  if (type == XCB_KEY_RELEASE)
    {
      win->key_down = 0;
      f = win->hook[XCB_KEY_RELEASE];
      if (f)
	f((unsigned int)ks, win->hook_param[XCB_KEY_RELEASE]);
      return ;
    }
  if (win->key_down && win->key_code == ev->detail)
    return ;
  win->key_down = 1;
  win->key_code = ev->detail;
  f = win->hook[XCB_KEY_PRESS];
  if (f)
    f((unsigned int)ks, win->hook_param[XCB_KEY_PRESS]);
}

void mlx__xcb_event_mouse(mlx__xcb_t *mlx_xcb, mlx__xcb_win_t *win,
			  xcb_key_press_event_t *ev)
{
  int	(*f)(unsigned int, unsigned int, unsigned int, void *);

  f = win->hook[ev->response_type];
  if (!f)
    return ;
  f((unsigned int)ev->detail, (unsigned int)ev->event_x,
    (unsigned int)ev->event_y, win->hook_param[ev->response_type]);
}

void mlx__xcb_event_motion(mlx__xcb_t *mlx_xcb, mlx__xcb_win_t *win,
			   xcb_key_press_event_t *ev)
{
  int	(*f)(unsigned int, unsigned int, void *);

  f = win->hook[ev->response_type];
  if (!f)
    return ;
  f((unsigned int)ev->event_x, (unsigned int)ev->event_y,
    win->hook_param[ev->response_type]);
}


void mlx__xcb_event_generic(mlx__xcb_t *mlx_xcb, mlx__xcb_win_t *win,
			    xcb_key_press_event_t *ev)
{
  int	(*f)(void *);

  f = win->hook[ev->response_type];
  if (!f)
    return ;
  f(win->hook_param[ev->response_type]);
}
