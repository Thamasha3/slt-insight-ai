import { Link } from "react-router-dom";

export default function PendingPage() {
  return (
    <div className="space-y-4 text-center">
      <h2 className="text-lg font-medium text-slate-800">Awaiting approval</h2>
      <p className="text-sm text-slate-600">
        Your registration is <strong>PENDING</strong>. An administrator must approve your account before you can sign
        in. You will not receive a token until then.
      </p>
      <Link to="/login" className="inline-block text-sm text-teal-800 underline">
        Return to sign in
      </Link>
    </div>
  );
}
