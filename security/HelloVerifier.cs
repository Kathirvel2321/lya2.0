// Window-bound Windows Hello verification. No credentials are read by LYA.
using System;
using System.Runtime.InteropServices;
using System.Threading;
using System.Diagnostics;
using System.Text.RegularExpressions;
using Windows.Foundation;
using Windows.Security.Credentials.UI;

class HelloVerifier
{
    [DllImport("combase.dll", PreserveSig = true)]
    static extern int RoInitialize(uint type);
    [DllImport("combase.dll")]
    static extern void RoUninitialize();
    [DllImport("combase.dll", CharSet = CharSet.Unicode)]
    static extern int WindowsCreateString(string text, uint length, out IntPtr value);
    [DllImport("combase.dll")]
    static extern int WindowsDeleteString(IntPtr value);
    [DllImport("combase.dll")]
    static extern int RoGetActivationFactory(IntPtr name, ref Guid iid,
        [MarshalAs(UnmanagedType.Interface)] out IVerifier factory);
    [DllImport("user32.dll")]
    static extern bool IsWindow(IntPtr hwnd);

    [ComImport, Guid("39E050C3-4E74-441A-8DC0-B81104DF949C"),
     InterfaceType(ComInterfaceType.InterfaceIsIInspectable)]
    interface IVerifier
    {
        void RequestVerificationForWindowAsync(IntPtr hwnd, IntPtr message,
            ref Guid iid, [MarshalAs(UnmanagedType.Interface)] out object operation);
    }

    static T Wait<T>(IAsyncOperation<T> operation)
    {
        var timer = Stopwatch.StartNew();
        try
        {
            while (operation.Status == AsyncStatus.Started)
            {
                if (timer.ElapsedMilliseconds >= 90000)
                {
                    operation.Cancel();
                    throw new TimeoutException();
                }
                Thread.Sleep(80);
            }
            if (operation.Status != AsyncStatus.Completed)
                throw new InvalidOperationException();
            return operation.GetResults();
        }
        finally { operation.Close(); }
    }

    static int Run(string[] args)
    {
        var availability = Wait(UserConsentVerifier.CheckAvailabilityAsync());
        if (args.Length == 1 && args[0] == "check")
        {
            Console.WriteLine(availability.ToString());
            return 0;
        }
        long handle;
        if (args.Length != 3 || args[0] != "verify" ||
            !long.TryParse(args[1], out handle) || !IsWindow(new IntPtr(handle)) ||
            !Regex.IsMatch(args[2], "^[A-Za-z0-9_-]{32}$"))
            return 2;
        if (availability != UserConsentVerifierAvailability.Available)
        {
            Console.WriteLine(availability.ToString());
            return 3;
        }
        IntPtr name = IntPtr.Zero, message = IntPtr.Zero;
        IVerifier factory = null;
        try
        {
            string className = "Windows.Security.Credentials.UI.UserConsentVerifier";
            Marshal.ThrowExceptionForHR(WindowsCreateString(className, (uint)className.Length, out name));
            string prompt = "LYA: verify your Windows account for administrator setup. This does not enroll face or voice.";
            Marshal.ThrowExceptionForHR(WindowsCreateString(prompt, (uint)prompt.Length, out message));
            Guid iid = typeof(IVerifier).GUID;
            Marshal.ThrowExceptionForHR(RoGetActivationFactory(name, ref iid, out factory));
            Guid asyncId = typeof(IAsyncOperation<UserConsentVerificationResult>).GUID;
            object raw;
            factory.RequestVerificationForWindowAsync(new IntPtr(handle), message, ref asyncId, out raw);
            var operation = (IAsyncOperation<UserConsentVerificationResult>)raw;
            var result = Wait(operation);
            Console.WriteLine(result == UserConsentVerificationResult.Verified ? "Verified:" + args[2] : result.ToString());
            return result == UserConsentVerificationResult.Verified ? 0 : 3;
        }
        finally
        {
            if (factory != null) Marshal.ReleaseComObject(factory);
            if (message != IntPtr.Zero) WindowsDeleteString(message);
            if (name != IntPtr.Zero) WindowsDeleteString(name);
        }
    }

    static int Main(string[] args)
    {
        int hr = RoInitialize(1);
        if (hr < 0) return 5;
        try { return Run(args); }
        catch (TimeoutException) { Console.WriteLine("TimedOut"); return 4; }
        catch { Console.WriteLine("Unavailable"); return 5; }
        finally { RoUninitialize(); }
    }
}
