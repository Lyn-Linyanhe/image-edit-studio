/* 最小 X11 客户端：验证 WSLg 的 X 服务器是否真的接受并映射窗口。
 *
 * 为什么不用 xdpyinfo/xeyes：本机免密 sudo 不可用，不擅自获取密码装包。
 * 这里直接声明 Xlib 原型并链接运行库（libX11.so.6），只用 gcc 即可编译。
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

typedef struct _XDisplay Display;
typedef unsigned long Window;
typedef unsigned long XID;
typedef int Bool;

typedef struct {
    int x, y;
    int width, height;
    int border_width;
    int depth;
    void *visual;
    Window root;
    int class;
    int bit_gravity;
    int win_gravity;
    int backing_store;
    unsigned long backing_planes;
    unsigned long backing_pixel;
    Bool save_under;
    XID colormap;
    Bool map_installed;
    int map_state;
    long all_event_masks;
    long your_event_mask;
    long do_not_propagate_mask;
    Bool override_redirect;
    XID screen;
} XWindowAttributes;

extern Display *XOpenDisplay(const char *);
extern Window XDefaultRootWindow(Display *);
extern Window XCreateSimpleWindow(Display *, Window, int, int, unsigned int,
                                  unsigned int, unsigned int, unsigned long, unsigned long);
extern int XStoreName(Display *, Window, const char *);
extern int XMapWindow(Display *, Window);
extern int XFlush(Display *);
extern int XGetWindowAttributes(Display *, Window, XWindowAttributes *);
extern int XDestroyWindow(Display *, Window);
extern int XCloseDisplay(Display *);

int main(void)
{
    const char *dpy_env = getenv("DISPLAY");
    Display *d = XOpenDisplay(NULL);
    if (!d) {
        printf("XOpenDisplay=FAILED (DISPLAY=%s)\n", dpy_env ? dpy_env : "(unset)");
        return 1;
    }
    printf("XOpenDisplay=OK (DISPLAY=%s)\n", dpy_env ? dpy_env : "(null)");

    Window root = XDefaultRootWindow(d);
    Window w = XCreateSimpleWindow(d, root, 120, 120, 320, 160, 2, 0xFFFFFFUL, 0x203040UL);
    XStoreName(d, w, "WSLg-test");
    XMapWindow(d, w);
    XFlush(d);
    usleep(1200000);   /* 留时间给合成器映射；用户屏幕上会闪一个小窗口 */

    XWindowAttributes a;
    if (XGetWindowAttributes(d, w, &a)) {
        printf("window_map_state=%d (2=IsViewable 表示真的上屏了)\n", a.map_state);
        printf("window_geometry=%dx%d+%d+%d\n", a.width, a.height, a.x, a.y);
    } else {
        printf("XGetWindowAttributes=FAILED\n");
    }

    XDestroyWindow(d, w);
    XCloseDisplay(d);
    printf("X11_CLIENT=DONE\n");
    return 0;
}
